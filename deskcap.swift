// deskcap — spike-zero capture tool for Cono.
// Opens the macOS Desk View virtual camera (or any camera) and saves a JPEG every N seconds.
// Also prints a cheap "how much changed since last frame" number so you can see whether
// ink-diff gating is viable before writing the real pipeline.
//
// Build (macOS 13+, Xcode command-line tools):
//   swiftc -O -framework AppKit -framework AVFoundation -framework CoreImage -framework ImageIO -o deskcap deskcap.swift
// Run:
//   ./deskcap --list
//   ./deskcap --interval 10 --out ~/deskcap-session1
//   ./deskcap --device default --interval 5          # plain FaceTime cam for comparison
//   ./deskcap --device "iPhone" --interval 10         # Continuity Camera Desk View by name substring
//
// First run triggers the camera permission prompt (attributed to Terminal/iTerm). Approve it.

import AppKit
import AVFoundation
import CoreImage
import Foundation
import ImageIO

// MARK: - CLI args

struct Options {
    var list = false
    var interval: Double = 10
    var out = FileManager.default.currentDirectoryPath + "/deskcap-" + Options.stamp()
    var device = "deskview"          // deskview | default | <name substring>
    var count = Int.max              // stop after N captures
    var quality: CGFloat = 0.9
    var noDiff = false
    var preview = false
    var streamFPS: Double = 0        // >0: emit length-prefixed JPEGs on stdout for live view
    var noWait = false               // fail if the camera is missing instead of waiting for it
    var setup = false                // open Apple's Desk View window in set-up mode (re-frame the desk crop)

    static func stamp() -> String {
        let f = DateFormatter(); f.dateFormat = "yyyyMMdd-HHmmss"; return f.string(from: Date())
    }
}

func parseArgs() -> Options {
    var o = Options()
    var it = CommandLine.arguments.dropFirst().makeIterator()
    func next(_ flag: String) -> String {
        guard let v = it.next() else { fail("missing value for \(flag)") }
        return v
    }
    while let a = it.next() {
        switch a {
        case "--list", "-l": o.list = true
        case "--interval", "-i":
            guard let v = Double(next(a)), v > 0 else { fail("bad interval") }
            o.interval = v
        case "--out", "-o": o.out = (next(a) as NSString).expandingTildeInPath
        case "--device", "-d": o.device = next(a)
        case "--count", "-n":
            guard let v = Int(next(a)), v > 0 else { fail("bad count") }
            o.count = v
        case "--quality", "-q": o.quality = CGFloat(Double(next(a)) ?? 0.9)
        case "--no-diff": o.noDiff = true
        case "--no-wait": o.noWait = true
        case "--setup": o.setup = true
        case "--preview", "-p": o.preview = true
        case "--stream", "-s":
            guard let v = Double(next(a)), v > 0 else { fail("bad stream fps") }
            o.streamFPS = v
        case "--help", "-h":
            print("""
            deskcap [--list] [--device deskview|default|<name>] [--interval SEC] [--out DIR]
                    [--count N] [--quality 0..1] [--no-diff] [--preview] [--no-wait]
            deskcap --setup   open Apple's Desk View window in set-up mode so the desk crop can be
                              re-framed (drag the corners, then start Desk View); exits when done
            The camera may come and go (an iPhone Desk View drops when the phone is
            unlocked or moved); deskcap waits for it and reattaches by itself, reporting
            "deskcap status: …" lines on stderr. --no-wait exits instead.
            """); exit(0)
        default: fail("unknown arg \(a)")
        }
    }
    return o
}

func fail(_ msg: String) -> Never {
    FileHandle.standardError.write(("deskcap: " + msg + "\n").data(using: .utf8)!)
    exit(1)
}

/// Machine-readable state for a supervisor (cono): "waiting …", "lost …", "live".
func status(_ s: String) { log("deskcap status: " + s) }

func log(_ s: String) {
    // stderr, so stdout stays clean for --stream frame data
    let f = DateFormatter(); f.dateFormat = "HH:mm:ss.SSS"
    FileHandle.standardError.write(("[\(f.string(from: Date()))] \(s)\n").data(using: .utf8)!)
}

// MARK: - Device discovery

func allVideoDevices() -> [AVCaptureDevice] {
    var types: [AVCaptureDevice.DeviceType] = [.deskViewCamera, .builtInWideAngleCamera]
    if #available(macOS 14.0, *) {
        types.append(contentsOf: [.continuityCamera, .external])
    }
    return AVCaptureDevice.DiscoverySession(deviceTypes: types, mediaType: .video, position: .unspecified).devices
}

func describe(_ d: AVCaptureDevice) -> String {
    let fmts = d.formats.map { f -> String in
        let dim = CMVideoFormatDescriptionGetDimensions(f.formatDescription)
        let fps = f.videoSupportedFrameRateRanges.map { Int($0.maxFrameRate) }.max() ?? 0
        let sub = CMFormatDescriptionGetMediaSubType(f.formatDescription)
        let cc = String(format: "%c%c%c%c", (sub >> 24) & 255, (sub >> 16) & 255, (sub >> 8) & 255, sub & 255)
        return "\(dim.width)x\(dim.height)@\(fps) \(cc)"
    }
    let uniq = Array(NSOrderedSet(array: fmts)) as! [String]
    return "\(d.localizedName)  type=\(d.deviceType.rawValue)  id=\(d.uniqueID)\n      formats: \(uniq.prefix(6).joined(separator: ", "))\(uniq.count > 6 ? " …(+\(uniq.count - 6))" : "")"
}

func findDevice(_ spec: String) -> AVCaptureDevice? {
    let devs = allVideoDevices()
    switch spec.lowercased() {
    case "deskview": return devs.first(where: { $0.deviceType == .deskViewCamera })
    case "default": return AVCaptureDevice.default(for: .video)
    default: return devs.first(where: { $0.localizedName.localizedCaseInsensitiveContains(spec) || $0.uniqueID == spec })
    }
}

func missingHint(_ spec: String) -> String {
    switch spec.lowercased() {
    case "deskview":
        return "no Desk View camera found. Built-in Desk View needs an M4+ MacBook Pro (2024+) / Air (2025+) / iMac M4; otherwise pair an iPhone 11+ via Continuity Camera (locked, on the lid, same Apple ID). Run --list to see what's here."
    case "default": return "no default camera"
    default: return "no camera matching '\(spec)'"
    }
}

// MARK: - Frame sink

final class FrameSink: NSObject, AVCaptureVideoDataOutputSampleBufferDelegate {
    private let lock = NSLock()
    private var latest: CVPixelBuffer?
    private(set) var frames = 0

    func captureOutput(_ output: AVCaptureOutput, didOutput sampleBuffer: CMSampleBuffer, from connection: AVCaptureConnection) {
        guard let pb = CMSampleBufferGetImageBuffer(sampleBuffer) else { return }
        lock.lock(); latest = pb; frames += 1; lock.unlock()
    }

    func take() -> CVPixelBuffer? {
        lock.lock(); defer { lock.unlock() }
        return latest
    }

    func clear() { lock.lock(); latest = nil; lock.unlock() }
}

// MARK: - Diff (cheap change signal: fraction of pixels whose gray value moved > 24/255 on a 192x144 thumbnail)

final class Differ {
    private let ctx = CIContext(options: [.useSoftwareRenderer: false])
    private var prev: [UInt8]?
    private let w = 192, h = 144

    func score(_ img: CIImage) -> (changed: Double, meanAbs: Double)? {
        let scale = CGFloat(w) / img.extent.width
        let small = img
            .transformed(by: CGAffineTransform(scaleX: scale, y: scale))
            .applyingFilter("CIColorControls", parameters: [kCIInputSaturationKey: 0])
        var buf = [UInt8](repeating: 0, count: w * h * 4)
        ctx.render(small, toBitmap: &buf, rowBytes: w * 4,
                   bounds: CGRect(x: 0, y: 0, width: w, height: h),
                   format: .RGBA8, colorSpace: CGColorSpaceCreateDeviceRGB())
        let gray = stride(from: 0, to: buf.count, by: 4).map { buf[$0] }
        defer { prev = gray }
        guard let p = prev else { return nil }
        var changed = 0, sum = 0
        for i in 0..<gray.count {
            let d = abs(Int(gray[i]) - Int(p[i]))
            sum += d
            if d > 24 { changed += 1 }
        }
        return (Double(changed) / Double(gray.count), Double(sum) / Double(gray.count))
    }
}

// MARK: - Main

let opts = parseArgs()

if opts.list {
    let devs = allVideoDevices()
    if devs.isEmpty { print("no video devices") }
    for d in devs { print("• " + describe(d)) }
    if let main = AVCaptureDevice.default(for: .video) {
        if #available(macOS 13.0, *), let c = main.companionDeskViewCamera {
            print("companionDeskViewCamera of '\(main.localizedName)': \(c.localizedName)")
        } else {
            print("companionDeskViewCamera of '\(main.localizedName)': none (no Desk View on this camera)")
        }
    }
    exit(0)
}

if opts.setup {
    // Apple's Desk View app owns the crop: it launches in set-up mode showing the
    // full ultra-wide view with the trapezoid that becomes the Desk View camera's
    // frame. We just present it and report back when the user finishes.
    guard #available(macOS 13.0, *) else { fail("Desk View set-up needs macOS 13 or later") }
    let cfg = AVCaptureDeskViewApplication.LaunchConfiguration()
    cfg.requiresSetUpModeCompletion = true
    status("setup — adjusting the Desk View framing")
    AVCaptureDeskViewApplication().present(launchConfiguration: cfg) { err in
        if let err = err { fail("Desk View set-up failed: \(err.localizedDescription)") }
        status("setup done")
        exit(0)
    }
    RunLoop.main.run()
}

// Permission
let sema = DispatchSemaphore(value: 0)
var granted = AVCaptureDevice.authorizationStatus(for: .video) == .authorized
if !granted {
    AVCaptureDevice.requestAccess(for: .video) { ok in granted = ok; sema.signal() }
    sema.wait()
}
guard granted else { fail("camera permission denied (System Settings → Privacy & Security → Camera)") }

try? FileManager.default.createDirectory(atPath: opts.out, withIntermediateDirectories: true)

let session = AVCaptureSession()
let output = AVCaptureVideoDataOutput()
output.alwaysDiscardsLateVideoFrames = true
output.videoSettings = [kCVPixelBufferPixelFormatTypeKey as String: kCVPixelFormatType_32BGRA]
let sink = FrameSink()
output.setSampleBufferDelegate(sink, queue: DispatchQueue(label: "deskcap.frames"))
session.beginConfiguration()
guard session.canAddOutput(output) else { fail("cannot add output") }
session.addOutput(output)
session.commitConfiguration()

// The camera is not a fixture: an iPhone Desk View vanishes when the phone is
// unlocked, picked up or wanders off, and comes back as a *new* device. So the
// input is attached and re-attached at runtime, and a watchdog treats a frame
// drought as a lost camera even when no disconnect notification arrives.
var currentInput: AVCaptureDeviceInput?
var currentDevice: AVCaptureDevice?
var waiting = false
var framesAtLastTick = 0
var lastProgress = Date()
let STALL_S: TimeInterval = 8

@discardableResult
func attach(_ d: AVCaptureDevice) -> Bool {
    session.beginConfiguration()
    if let old = currentInput { session.removeInput(old) }
    guard let input = try? AVCaptureDeviceInput(device: d), session.canAddInput(input) else {
        session.commitConfiguration()
        log("cannot open \(d.localizedName) — will keep trying")
        return false
    }
    session.addInput(input)
    session.commitConfiguration()
    currentInput = input
    currentDevice = d
    sink.clear()
    framesAtLastTick = 0
    lastProgress = Date()
    if !session.isRunning { session.startRunning() }
    let dim = CMVideoFormatDescriptionGetDimensions(d.activeFormat.formatDescription)
    log("device: \(d.localizedName) (\(d.deviceType.rawValue)) active format \(dim.width)x\(dim.height)")
    if waiting { waiting = false; status("live") }
    return true
}

func detach(_ why: String) {
    guard !waiting else { return }
    waiting = true
    if session.isRunning { session.stopRunning() }
    if let old = currentInput {
        session.beginConfiguration(); session.removeInput(old); session.commitConfiguration()
    }
    currentInput = nil
    currentDevice = nil
    sink.clear()
    status("lost (\(why)) — waiting for the camera to come back")
}

if let d = findDevice(opts.device), attach(d) {
    // attached on the first try
} else if opts.noWait {
    fail(missingHint(opts.device))
} else {
    waiting = true
    status("waiting — " + missingHint(opts.device))
}
log("saving every \(opts.interval)s → \(opts.out)   (Ctrl-C to stop)")

NotificationCenter.default.addObserver(forName: AVCaptureDevice.wasDisconnectedNotification, object: nil, queue: .main) { n in
    if let d = n.object as? AVCaptureDevice, d.uniqueID == currentDevice?.uniqueID { detach("disconnected") }
}
NotificationCenter.default.addObserver(forName: AVCaptureSession.runtimeErrorNotification, object: session, queue: .main) { n in
    let why = (n.userInfo?[AVCaptureSessionErrorKey] as? NSError)?.localizedDescription ?? "runtime error"
    detach(why)
}
let watchdog = Timer(fire: Date().addingTimeInterval(2), interval: 2, repeats: true) { _ in
    if waiting {
        if let d = findDevice(opts.device) { attach(d) }
        return
    }
    let n = sink.frames
    if n != framesAtLastTick { framesAtLastTick = n; lastProgress = Date(); return }
    if Date().timeIntervalSince(lastProgress) > STALL_S { detach("no frames for \(Int(STALL_S)) s") }
}
RunLoop.main.add(watchdog, forMode: .common)

let ciCtx = CIContext()
let differ = Differ()
var shot = 0
let csvURL = URL(fileURLWithPath: opts.out).appendingPathComponent("log.csv")
try? "n,timestamp,file,width,height,bytes,changed_frac,mean_abs_diff,frames_seen\n".write(to: csvURL, atomically: true, encoding: .utf8)

signal(SIGINT) { _ in FileHandle.standardError.write("\nstopped\n".data(using: .utf8)!); exit(0) }

// Give the camera a moment to expose before the first shot.
let timer = Timer(fire: Date().addingTimeInterval(1.5), interval: opts.interval, repeats: true) { t in
    guard let pb = sink.take() else { if !waiting { log("no frame yet") }; return }
    shot += 1
    let img = CIImage(cvPixelBuffer: pb)
    let name = String(format: "frame-%04d.jpg", shot)
    let url = URL(fileURLWithPath: opts.out).appendingPathComponent(name)
    let cs = CGColorSpaceCreateDeviceRGB()
    var bytes = 0
    let q = CIImageRepresentationOption(rawValue: kCGImageDestinationLossyCompressionQuality as String)
    if let data = ciCtx.jpegRepresentation(of: img, colorSpace: cs, options: [q: opts.quality]) {
        try? data.write(to: url); bytes = data.count
    }
    var diffTxt = "", changed = "", mean = ""
    if !opts.noDiff, let s = differ.score(img) {
        changed = String(format: "%.4f", s.changed); mean = String(format: "%.2f", s.meanAbs)
        diffTxt = "  changed=\(String(format: "%.1f", s.changed * 100))%  meanΔ=\(mean)"
    }
    log("\(name) \(Int(img.extent.width))x\(Int(img.extent.height)) \(bytes / 1024)KB\(diffTxt)  (frames seen: \(sink.frames))")
    let row = "\(shot),\(ISO8601DateFormatter().string(from: Date())),\(name),\(Int(img.extent.width)),\(Int(img.extent.height)),\(bytes),\(changed),\(mean),\(sink.frames)\n"
    if let h = try? FileHandle(forWritingTo: csvURL) { h.seekToEndOfFile(); h.write(row.data(using: .utf8)!); h.closeFile() }
    if shot >= opts.count { log("done (\(shot) frames)"); t.invalidate(); exit(0) }
}
RunLoop.main.add(timer, forMode: .common)

if opts.streamFPS > 0 {
    // live view: latest frame as JPEG on stdout, 4-byte big-endian length prefix per frame
    let streamCtx = CIContext()
    let sq = CIImageRepresentationOption(rawValue: kCGImageDestinationLossyCompressionQuality as String)
    let streamTimer = Timer(fire: Date().addingTimeInterval(1.5), interval: 1.0 / opts.streamFPS, repeats: true) { _ in
        guard let pb = sink.take() else { return }
        var img = CIImage(cvPixelBuffer: pb)
        let maxW: CGFloat = 1280                      // display-only: smaller + softer than saved frames
        if img.extent.width > maxW {
            let s = maxW / img.extent.width
            img = img.transformed(by: CGAffineTransform(scaleX: s, y: s))
        }
        guard let data = streamCtx.jpegRepresentation(of: img, colorSpace: CGColorSpaceCreateDeviceRGB(),
                                                      options: [sq: 0.6]) else { return }
        var len = UInt32(data.count).bigEndian
        FileHandle.standardOutput.write(Data(bytes: &len, count: 4))
        FileHandle.standardOutput.write(data)
    }
    RunLoop.main.add(streamTimer, forMode: .common)
}

if opts.preview {
    let app = NSApplication.shared
    app.setActivationPolicy(.regular)
    let win = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 960, height: 720),
                       styleMask: [.titled, .closable, .resizable, .miniaturizable],
                       backing: .buffered, defer: false)
    win.title = "deskcap — \(currentDevice?.localizedName ?? opts.device)"
    let view = NSView(frame: win.contentView!.bounds)
    view.wantsLayer = true
    view.autoresizingMask = [.width, .height]
    let preview = AVCaptureVideoPreviewLayer(session: session)
    preview.videoGravity = .resizeAspect
    preview.frame = view.bounds
    preview.autoresizingMask = [.layerWidthSizable, .layerHeightSizable]
    view.layer?.addSublayer(preview)
    win.contentView = view
    win.center()
    win.makeKeyAndOrderFront(nil)
    app.activate(ignoringOtherApps: true)
    NotificationCenter.default.addObserver(forName: NSWindow.willCloseNotification, object: win, queue: .main) { _ in
        log("preview closed — stopping"); exit(0)
    }
    app.run()
} else {
    RunLoop.main.run()
}
