// Renders the Picture-in-Picture walkthrough shown while the user sets up call forwarding in
// the Phone app (iOS 27+, where Equal can only copy the code): Home › Phone, Keypad, touch and
// hold › Paste, Call, the carrier's confirmation, then back to Equal AI.
//
//   swift tools/render_forwarding_guide.swift EqualOrbOnboarding/Resources/Video/forwarding_guide.mp4 [stills-folder]
//
// Run it from the repo root: the Home screen's wallpaper is tools/assets/home_wallpaper.webp.
//
// Every frame is a pure function of time, drawn with SwiftUI and encoded to H.264.

import AVFoundation
import AppKit
import SwiftUI

let size = CGSize(width: 360, height: 480)
let phoneH: CGFloat = 400
let scale: CGFloat = 2
let fps: Int32 = 30
let duration = 12.0
let code = "**67*04048938092#"

// MARK: Timeline

func ramp(_ t: Double, _ a: Double, _ b: Double) -> Double {
    let x = min(max((t - a) / (b - a), 0), 1)
    return x * x * (3 - 2 * x)
}

/// Taps: (time, point in the phone area, long press).
let taps: [(Double, CGPoint, Bool)] = [
    (1.5, CGPoint(x: 62, y: 359), false),     // Phone, in the dock
    (3.5, CGPoint(x: 180, y: 52), true),      // touch and hold the number field
    (4.6, CGPoint(x: 180, y: 20), false),     // Paste
    (6.4, CGPoint(x: 180, y: 353), false),    // Call
]
let openPhone = 1.75          // Home → Phone (keypad)
let pasted = 4.75             // the code appears
let dialled = 6.6             // the call starts; the carrier replies
let answered = 7.6

struct Caption { let from: Double; let step: String; let text: String }
let captions = [
    Caption(from: 0, step: "Step 1 of 3", text: "Go Home and open Phone"),
    Caption(from: 2.6, step: "Step 2 of 3", text: "Keypad: touch and hold, then Paste"),
    Caption(from: 5.4, step: "Step 3 of 3", text: "Tap the green Call button"),
    Caption(from: 9.4, step: "All set", text: "Now come back to Equal AI"),
]

// MARK: Drawing

let ios = Color(red: 0.95, green: 0.95, blue: 0.97)
let label = Color.black
let secondary = Color(white: 0.55)
let iosGreen = Color(red: 0.204, green: 0.78, blue: 0.349)
let equalGreen = Color(red: 0, green: 0.694, blue: 0.251)
/// The border: Equal green at about 45 %, on white. Present, but soft.
let frameGreen = Color(red: 0.55, green: 0.862, blue: 0.663)

// MARK: Home screen

/// iOS's app-icon shape: a continuous rounded square.
struct IconShape: View {
    var fill: AnyShapeStyle
    var body: some View {
        RoundedRectangle(cornerRadius: iconSize * 0.225, style: .continuous).fill(fill)
            .overlay(RoundedRectangle(cornerRadius: iconSize * 0.225, style: .continuous)
                .strokeBorder(.black.opacity(0.06), lineWidth: 0.5))
            .frame(width: iconSize, height: iconSize)
    }
}

let iconSize: CGFloat = 54

func grad(_ top: UInt32, _ bottom: UInt32) -> AnyShapeStyle {
    AnyShapeStyle(LinearGradient(colors: [Color(hex: top), Color(hex: bottom)], startPoint: .top, endPoint: .bottom))
}

extension Color {
    init(hex: UInt32) {
        self.init(red: Double(hex >> 16 & 0xFF) / 255, green: Double(hex >> 8 & 0xFF) / 255, blue: Double(hex & 0xFF) / 255)
    }
}

/// App icons drawn after iOS's own, at home-screen size.
struct AppArt: View {
    let app: String
    var body: some View {
        let s = iconSize
        ZStack {
            switch app {
            case "Phone":
                IconShape(fill: grad(0x6BF27E, 0x1EC33B))
                Image(systemName: "phone.fill").font(.system(size: s * 0.5)).foregroundStyle(.white)
            case "Messages":
                IconShape(fill: grad(0x6BF27E, 0x1EC33B))
                Image(systemName: "message.fill").font(.system(size: s * 0.52)).foregroundStyle(.white)
            case "Music":
                IconShape(fill: grad(0xFC6079, 0xF9243E))
                Image(systemName: "music.note").font(.system(size: s * 0.5, weight: .semibold)).foregroundStyle(.white)
            case "Safari":
                IconShape(fill: grad(0xFFFFFF, 0xE4E4E9))
                Circle().fill(LinearGradient(colors: [Color(hex: 0x1BB4FC), Color(hex: 0x1462EE)], startPoint: .top, endPoint: .bottom))
                    .frame(width: s * 0.8)
                ForEach(0..<36, id: \.self) { i in
                    Capsule().fill(.white.opacity(i % 3 == 0 ? 0.95 : 0.6))
                        .frame(width: 0.7, height: i % 3 == 0 ? s * 0.07 : s * 0.045)
                        .offset(y: -s * 0.33).rotationEffect(.degrees(Double(i) * 10))
                }
                ZStack {
                    Triangle().fill(Color(hex: 0xFF3B30)).frame(width: s * 0.1, height: s * 0.3).offset(y: -s * 0.15)
                    Triangle().fill(.white).frame(width: s * 0.1, height: s * 0.3).rotationEffect(.degrees(180)).offset(y: s * 0.15)
                }
                .rotationEffect(.degrees(45))
            case "Calendar":
                IconShape(fill: AnyShapeStyle(Color.white))
                VStack(spacing: -2) {
                    Text("THURSDAY").font(.system(size: s * 0.15, weight: .semibold)).foregroundStyle(Color(hex: 0xFF3B30))
                    Text("12").font(.system(size: s * 0.52, weight: .light)).foregroundStyle(.black)
                }
                .offset(y: 1)
            case "Photos":
                IconShape(fill: AnyShapeStyle(Color.white))
                let petals: [UInt32] = [0xFDB827, 0xF7882F, 0xF0505B, 0xD6439B, 0x8B5BD6, 0x3F8CF2, 0x35C2C9, 0x7DCB4D]
                ForEach(0..<8, id: \.self) { i in
                    Capsule().fill(Color(hex: petals[i]).opacity(0.82))
                        .frame(width: s * 0.2, height: s * 0.34)
                        .offset(y: -s * 0.14)
                        .rotationEffect(.degrees(Double(i) * 45))
                        .blendMode(.multiply)
                }
            case "Camera":
                IconShape(fill: grad(0xE6E6E9, 0xAFAFB4))
                RoundedRectangle(cornerRadius: s * 0.08, style: .continuous).fill(Color(hex: 0x2C2C2E))
                    .frame(width: s * 0.66, height: s * 0.44).offset(y: s * 0.04)
                Circle().fill(Color(hex: 0x8E8E93)).frame(width: s * 0.3).offset(y: s * 0.04)
                Circle().fill(Color(hex: 0x1C1C1E)).frame(width: s * 0.2).offset(y: s * 0.04)
                Circle().fill(Color(hex: 0x3E6FA6).opacity(0.8)).frame(width: s * 0.07).offset(x: -s * 0.03, y: s * 0.01)
            case "Mail":
                IconShape(fill: grad(0x5AC4FA, 0x1A72F2))
                Image(systemName: "envelope.fill").font(.system(size: s * 0.46)).foregroundStyle(.white)
            case "Clock":
                IconShape(fill: AnyShapeStyle(Color.black))
                Circle().fill(.white).frame(width: s * 0.84)
                ForEach(0..<12, id: \.self) { i in
                    Text("\(i == 0 ? 12 : i)").font(.system(size: s * 0.1, weight: .medium)).foregroundStyle(.black)
                        .offset(y: -s * 0.32).rotationEffect(.degrees(Double(i) * 30))
                }
                Capsule().fill(.black).frame(width: s * 0.045, height: s * 0.22).offset(y: -s * 0.09).rotationEffect(.degrees(305))
                Capsule().fill(.black).frame(width: s * 0.045, height: s * 0.32).offset(y: -s * 0.14).rotationEffect(.degrees(50))
                Capsule().fill(Color(hex: 0xFF9500)).frame(width: s * 0.018, height: s * 0.38).offset(y: -s * 0.14).rotationEffect(.degrees(160))
                Circle().fill(Color(hex: 0xFF9500)).frame(width: s * 0.06)
            case "Weather":
                IconShape(fill: grad(0x1C6BE0, 0x5AB6F6))
                Image(systemName: "cloud.sun.fill").symbolRenderingMode(.palette)
                    .foregroundStyle(.white, Color(hex: 0xFFD60A))
                    .font(.system(size: s * 0.46))
            case "Notes":
                IconShape(fill: AnyShapeStyle(Color.white))
                VStack(spacing: 0) {
                    Rectangle().fill(LinearGradient(colors: [Color(hex: 0xFFDD55), Color(hex: 0xFFC92E)], startPoint: .top, endPoint: .bottom))
                        .frame(height: s * 0.27)
                    Rectangle().fill(Color(white: 0.75)).frame(height: 0.6).padding(.top, s * 0.03)
                    ForEach(0..<3, id: \.self) { _ in
                        Rectangle().fill(Color(white: 0.86)).frame(height: 0.6).padding(.top, s * 0.13)
                    }
                    Spacer()
                }
                .frame(width: s, height: s)
                .clipShape(RoundedRectangle(cornerRadius: s * 0.225, style: .continuous))
            case "Reminders":
                IconShape(fill: AnyShapeStyle(Color.white))
                VStack(alignment: .leading, spacing: s * 0.08) {
                    ForEach([0x0A84FF, 0xFF453A, 0xFF9F0A] as [UInt32], id: \.self) { c in
                        HStack(spacing: s * 0.07) {
                            Circle().strokeBorder(Color(hex: c), lineWidth: 1.4)
                                .background(Circle().fill(Color(hex: c)).padding(2.2))
                                .frame(width: s * 0.15, height: s * 0.15)
                            Capsule().fill(Color(white: 0.85)).frame(width: s * 0.42, height: 1.2)
                        }
                    }
                }
            case "Health":
                IconShape(fill: AnyShapeStyle(Color.white))
                Image(systemName: "heart.fill").font(.system(size: s * 0.4))
                    .foregroundStyle(LinearGradient(colors: [Color(hex: 0xFF6B8B), Color(hex: 0xFF2D55)], startPoint: .top, endPoint: .bottom))
                    .offset(x: s * 0.17, y: -s * 0.17)
            case "Wallet":
                IconShape(fill: AnyShapeStyle(Color.black))
                VStack(spacing: -s * 0.1) {
                    ForEach([0x30B0C7, 0xFFCC00, 0x34C759, 0xFF6B4A] as [UInt32], id: \.self) { c in
                        RoundedRectangle(cornerRadius: s * 0.05).fill(Color(hex: c)).frame(width: s * 0.66, height: s * 0.18)
                    }
                }
                .offset(y: -s * 0.02)
                RoundedRectangle(cornerRadius: s * 0.06).fill(Color(hex: 0xD9D9DE))
                    .frame(width: s * 0.72, height: s * 0.26).offset(y: s * 0.19)
            case "Calculator":
                IconShape(fill: AnyShapeStyle(Color(hex: 0x1C1C1E)))
                VStack(spacing: s * 0.06) {
                    ForEach(0..<3, id: \.self) { r in
                        HStack(spacing: s * 0.06) {
                            ForEach(0..<3, id: \.self) { c in
                                Circle().fill(c == 2 ? Color(hex: 0xFF9F0A) : (r == 0 ? Color(hex: 0xA5A5A5) : Color(hex: 0x505050)))
                                    .frame(width: s * 0.18)
                            }
                        }
                    }
                }
            default: // Settings
                IconShape(fill: grad(0xE3E3E6, 0x9B9BA1))
                Image(systemName: "gearshape.fill").font(.system(size: s * 0.66, weight: .regular))
                    .foregroundStyle(LinearGradient(colors: [Color(hex: 0x5D5D62), Color(hex: 0x3A3A3E)], startPoint: .top, endPoint: .bottom))
            }
        }
        .frame(width: s, height: s)
        .clipShape(RoundedRectangle(cornerRadius: s * 0.225, style: .continuous))
    }
}

struct Triangle: Shape {
    func path(in r: CGRect) -> Path {
        Path { p in p.move(to: CGPoint(x: r.midX, y: r.minY)); p.addLine(to: CGPoint(x: r.maxX, y: r.maxY)); p.addLine(to: CGPoint(x: r.minX, y: r.maxY)); p.closeSubpath() }
    }
}

/// An app on the Home screen: its icon and its name underneath.
struct HomeApp: View {
    let name: String
    var labelled = true
    var body: some View {
        VStack(spacing: 4) {
            AppArt(app: name).shadow(color: .black.opacity(0.12), radius: 3, y: 1)
            if labelled {
                Text(name).font(.system(size: 11, weight: .regular)).foregroundStyle(.white)
                    .shadow(color: .black.opacity(0.35), radius: 2, y: 0.5)
                    .lineLimit(1).fixedSize()
            }
        }
    }
}

/// The wallpaper (iOS's blue one, as in the voicemail walkthrough), filling the phone area.
let wallpaper: NSImage = {
    guard let img = NSImage(contentsOfFile: "tools/assets/home_wallpaper.webp") else {
        fatalError("run from the repo root: tools/assets/home_wallpaper.webp not found")
    }
    return img
}()

/// Column centres of the 4-wide app grid (the dock uses the same ones).
let homeColumns: [CGFloat] = [62, 140.67, 219.33, 298]
let dockY: CGFloat = 359

/// The Home screen as on a real iPhone: status bar, three rows of apps with their names, the
/// Search pill, and the frosted dock with Phone first.
struct HomeScreen: View {
    let rows = [["Calendar", "Photos", "Camera", "Mail"],
                ["Clock", "Weather", "Notes", "Reminders"],
                ["Health", "Wallet", "Calculator", "Settings"]]
    let dock = ["Phone", "Safari", "Messages", "Music"]

    var paper: some View {
        Image(nsImage: wallpaper).resizable().aspectRatio(contentMode: .fill)
            .frame(width: size.width, height: phoneH).clipped()
    }

    var body: some View {
        ZStack(alignment: .topLeading) {
            paper
            // Status bar
            HStack {
                Text("9:41").font(.system(size: 15, weight: .semibold))
                Spacer()
                HStack(spacing: 5) {
                    Image(systemName: "cellularbars")
                    Image(systemName: "wifi")
                    Image(systemName: "battery.100")
                }
                .font(.system(size: 13, weight: .semibold))
            }
            .foregroundStyle(.white)
            .padding(.horizontal, 30)
            .frame(width: size.width, height: 34)
            // Apps
            ForEach(rows.indices, id: \.self) { r in
                ForEach(rows[r].indices, id: \.self) { c in
                    HomeApp(name: rows[r][c]).position(x: homeColumns[c], y: 76 + CGFloat(r) * 84)
                }
            }
            // Search
            HStack(spacing: 4) {
                Image(systemName: "magnifyingglass").font(.system(size: 10.5, weight: .semibold))
                Text("Search").font(.system(size: 12, weight: .medium))
            }
            .foregroundStyle(.white)
            .padding(.horizontal, 11)
            .frame(height: 24)
            .background(Capsule().fill(.white.opacity(0.22)))
            .position(x: size.width / 2, y: 306)
            // Dock: the wallpaper, blurred and lightened, behind the four apps.
            paper.blur(radius: 18).overlay(Color.white.opacity(0.24))
                .mask(RoundedRectangle(cornerRadius: 30, style: .continuous)
                    .frame(width: size.width - 20, height: 76).position(x: size.width / 2, y: dockY))
            RoundedRectangle(cornerRadius: 30, style: .continuous).strokeBorder(.white.opacity(0.25), lineWidth: 0.6)
                .frame(width: size.width - 20, height: 76).position(x: size.width / 2, y: dockY)
            ForEach(dock.indices, id: \.self) { c in
                HomeApp(name: dock[c], labelled: false).position(x: homeColumns[c], y: dockY)
            }
        }
        .frame(width: size.width, height: phoneH)
        .environment(\.colorScheme, .dark)
    }
}

/// Drawn once and reused: the Home screen doesn't change.
let homeImage: NSImage = MainActor.assumeIsolated {
    let r = ImageRenderer(content: HomeScreen())
    r.scale = scale
    return r.nsImage!
}

/// The Phone app's keypad, with the pasted code once it's in.
struct Keypad: View {
    let t: Double
    let keys = [["1", "2", "3"], ["4", "5", "6"], ["7", "8", "9"], ["*", "0", "#"]]
    var body: some View {
        let shown = t >= pasted
        VStack(spacing: 0) {
            Text(shown ? code : " ")
                .font(.system(size: 26, weight: .regular))
                .foregroundStyle(label)
                .frame(height: 50)
                .padding(.top, 26)
                .opacity(ramp(t, pasted, pasted + 0.2))
            VStack(spacing: 8) {
                ForEach(0..<4, id: \.self) { r in
                    HStack(spacing: 24) {
                        ForEach(keys[r], id: \.self) { k in
                            Text(k).font(.system(size: 24)).foregroundStyle(label)
                                .frame(width: 52, height: 52)
                                .background(Circle().fill(Color(white: 0.89)))
                        }
                    }
                }
            }
            .padding(.top, 8)
            Circle().fill(iosGreen).frame(width: 54, height: 54)
                .overlay(Image(systemName: "phone.fill").font(.system(size: 22)).foregroundStyle(.white))
                .padding(.top, 10)
            Spacer()
        }
        .frame(width: size.width, height: phoneH)
        .background(.white)
        .overlay(alignment: .top) {
            // The Paste menu above the number, after touch and hold.
            let k = ramp(t, 3.9, 4.1) * (1 - ramp(t, 4.7, 4.85))
            if k > 0 {
                Text("Paste").font(.system(size: 15, weight: .medium)).foregroundStyle(.white)
                    .padding(.horizontal, 16).frame(height: 34)
                    .background(RoundedRectangle(cornerRadius: 9, style: .continuous).fill(Color(white: 0.15)))
                    .padding(.top, 2)
                    .scaleEffect(0.8 + 0.2 * k).opacity(k)
            }
        }
    }
}

/// The carrier's reply once the code is dialled.
struct CarrierReply: View {
    var body: some View {
        VStack(spacing: 14) {
            Text("Calling…").font(.system(size: 15)).foregroundStyle(.white.opacity(0.6)).padding(.top, 70)
            Text("Setting Registration Succeeded").font(.system(size: 17, weight: .semibold)).foregroundStyle(.white)
            Text("Voice Call Forwarding").font(.system(size: 15)).foregroundStyle(.white.opacity(0.85))
            Text("Dismiss").font(.system(size: 16, weight: .semibold)).foregroundStyle(.black)
                .padding(.horizontal, 30).frame(height: 44)
                .background(Capsule().fill(.white))
                .padding(.top, 18)
            Spacer()
        }
        .frame(width: size.width, height: phoneH)
        .background(Color.black)
    }
}

struct Frame: View {
    let t: Double

    var body: some View {
        let caption = captions.last { t >= $0.from }!
        let done = caption.step == "All set"
        VStack(spacing: 0) {
            // Instruction banner: quiet, so the steps below stay the focus. White, a green glyph,
            // dark text, and a hairline to the phone.
            HStack(spacing: 12) {
                ZStack {
                    Circle().fill(equalGreen.opacity(0.1)).frame(width: 36, height: 36)
                    Image(systemName: done ? "checkmark" : "hand.tap.fill").font(.system(size: 16, weight: .semibold)).foregroundStyle(equalGreen)
                }
                VStack(alignment: .leading, spacing: 1) {
                    Text(caption.step.uppercased()).font(.system(size: 11.5, weight: .semibold)).foregroundStyle(secondary).tracking(0.6)
                    Text(caption.text).font(.system(size: 17, weight: .semibold)).foregroundStyle(label).lineLimit(2).minimumScaleFactor(0.8)
                }
                Spacer(minLength: 0)
            }
            .padding(.horizontal, 18)
            .frame(height: 80)
            .background(Color.white)
            .overlay(alignment: .bottom) { Rectangle().fill(Color.black.opacity(0.08)).frame(height: 1) }

            // Phone
            ZStack(alignment: .topLeading) {
                let open = ramp(t, openPhone, openPhone + 0.35)
                Image(nsImage: homeImage).resizable().frame(width: size.width, height: phoneH)
                    .scaleEffect(1 + 0.15 * open)
                    .opacity(1 - open)
                Keypad(t: t)
                    .scaleEffect(0.3 + 0.7 * open, anchor: UnitPoint(x: homeColumns[0] / size.width, y: dockY / phoneH))
                    .opacity(open)
                let reply = ramp(t, answered, answered + 0.35)
                if t > dialled {
                    CarrierReply().opacity(reply)
                }
                ForEach(taps.indices, id: \.self) { i in
                    let (at, p, hold) = taps[i]
                    let lift = hold ? 0.6 : 0.2
                    let a = ramp(t, at - 0.45, at - 0.15) * (1 - ramp(t, at + lift, at + lift + 0.25))
                    let press = ramp(t, at - 0.15, at) * (1 - ramp(t, at + lift, at + lift + 0.2))
                    if a > 0 {
                        Circle().fill(Color.black.opacity(0.18)).frame(width: 46, height: 46)
                            .overlay(Circle().stroke(.white, lineWidth: 3))
                            .scaleEffect(1 - 0.18 * press)
                            .opacity(a)
                            .position(p)
                            .zIndex(10)
                    }
                }
                if done {
                    let k = ramp(t, 9.4, 9.8)
                    ZStack {
                        Color.white.opacity(0.9 * k)
                        VStack(spacing: 12) {
                            Image(systemName: "checkmark.circle.fill").font(.system(size: 64)).foregroundStyle(equalGreen)
                            Text("Call forwarding is on.\nHead back to Equal AI").font(.system(size: 16, weight: .semibold))
                                .multilineTextAlignment(.center).foregroundStyle(label)
                        }
                        .scaleEffect(0.85 + 0.15 * k).opacity(k)
                    }
                    .frame(width: size.width, height: phoneH)
                    .zIndex(20)
                }
            }
            .frame(width: size.width, height: phoneH, alignment: .topLeading)
            .clipped()
        }
        .frame(width: size.width, height: size.height)
        .background(ios)
        .overlay(GreenFrame().fill(frameGreen, style: FillStyle(eoFill: true)))
        .environment(\.colorScheme, .light)
    }
}

/// Everything outside a rounded rectangle inset by the border width. The PiP window's corners
/// measure about 32 at this video size and it trims a few units off each edge, so the inner
/// corners use a 27 radius to run parallel to the window's curve instead of thinning out.
struct GreenFrame: Shape {
    var width: CGFloat = 7
    var innerRadius: CGFloat = 27
    func path(in r: CGRect) -> Path {
        var p = Path(r)
        p.addRoundedRect(in: r.insetBy(dx: width, dy: width),
                         cornerSize: CGSize(width: innerRadius, height: innerRadius), style: .continuous)
        return p
    }
}

// MARK: Encode

let out = URL(fileURLWithPath: CommandLine.arguments.count > 1 ? CommandLine.arguments[1] : "forwarding_guide.mp4")
try? FileManager.default.removeItem(at: out)
try FileManager.default.createDirectory(at: out.deletingLastPathComponent(), withIntermediateDirectories: true)

let w = Int(size.width * scale), h = Int(size.height * scale)
let writer = try AVAssetWriter(outputURL: out, fileType: .mp4)
let input = AVAssetWriterInput(mediaType: .video, outputSettings: [
    AVVideoCodecKey: AVVideoCodecType.h264, AVVideoWidthKey: w, AVVideoHeightKey: h,
    AVVideoCompressionPropertiesKey: [AVVideoAverageBitRateKey: 1_200_000],
])
let adaptor = AVAssetWriterInputPixelBufferAdaptor(assetWriterInput: input, sourcePixelBufferAttributes: [
    kCVPixelBufferPixelFormatTypeKey as String: kCVPixelFormatType_32ARGB, kCVPixelBufferWidthKey as String: w, kCVPixelBufferHeightKey as String: h,
])
writer.add(input)
writer.startWriting()
writer.startSession(atSourceTime: .zero)

let frames = Int(duration * Double(fps))
MainActor.assumeIsolated {
    for f in 0..<frames {
        let t = Double(f) / Double(fps)
        let r = ImageRenderer(content: Frame(t: t))
        r.scale = scale
        guard let cg = r.cgImage else { fatalError("render failed at \(t)") }
        var pb: CVPixelBuffer?
        CVPixelBufferPoolCreatePixelBuffer(nil, adaptor.pixelBufferPool!, &pb)
        let buf = pb!
        CVPixelBufferLockBaseAddress(buf, [])
        let ctx = CGContext(data: CVPixelBufferGetBaseAddress(buf), width: w, height: h, bitsPerComponent: 8,
                            bytesPerRow: CVPixelBufferGetBytesPerRow(buf), space: CGColorSpaceCreateDeviceRGB(),
                            bitmapInfo: CGImageAlphaInfo.noneSkipFirst.rawValue)!
        ctx.draw(cg, in: CGRect(x: 0, y: 0, width: w, height: h))
        CVPixelBufferUnlockBaseAddress(buf, [])
        while !input.isReadyForMoreMediaData { Thread.sleep(forTimeInterval: 0.005) }
        adaptor.append(buf, withPresentationTime: CMTime(value: CMTimeValue(f), timescale: fps))
        // Optional second argument: a folder for a few still frames to eyeball.
        if CommandLine.arguments.count > 2, [20, 60, 110, 140, 200, 250, 300, 340].contains(f), let png = NSBitmapImageRep(cgImage: cg).representation(using: .png, properties: [:]) {
            try? png.write(to: URL(fileURLWithPath: CommandLine.arguments[2]).appendingPathComponent("guide_\(f).png"))
        }
    }
}
input.markAsFinished()
let sem = DispatchSemaphore(value: 0)
writer.finishWriting { sem.signal() }
sem.wait()
print(writer.status == .completed ? "wrote \(out.path) (\(frames) frames)" : "failed: \(String(describing: writer.error))")
