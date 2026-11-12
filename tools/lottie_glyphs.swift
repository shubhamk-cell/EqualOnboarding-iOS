// Text → vector outlines for hand-built Lotties, so they need no fonts to play.
// Reads a JSON list of {id, text, font: "dm" | "sf", size, weight, tracking?, tnum?} on stdin and
// writes {id: {width, ascent, descent, leading, contours: [{v, i, o}]}} on stdout, in points,
// y down, origin at the left end of the baseline. DM Sans comes from the app's bundled file with
// its optical size following the point size, as in the app; "sf" is the system font.
// Run it from the repo root.
//
//   echo '[{"id":"a","text":"9:41","font":"sf","size":12,"weight":600}]' | swift tools/lottie_glyphs.swift

import AppKit
import CoreText
import Foundation

struct Req: Decodable {
    let id: String, text: String, font: String
    let size: Double, weight: Double
    let tracking: Double?
    let tnum: Bool?
}

// Run from the repo root (or pass the font's path).
let dmURL = URL(fileURLWithPath: CommandLine.arguments.count > 1 ? CommandLine.arguments[1]
                : "EqualOrbOnboarding/Resources/Fonts/DMSans.ttf")
let dmBase: CTFontDescriptor = {
    let ds = CTFontManagerCreateFontDescriptorsFromURL(dmURL as CFURL) as! [CTFontDescriptor]
    return ds[0]
}()

func tag(_ s: String) -> Int { s.utf8.reduce(0) { $0 << 8 | Int($1) } }

func font(_ r: Req) -> CTFont {
    var attrs: [CFString: Any] = [:]
    if r.tnum == true {
        attrs[kCTFontFeatureSettingsAttribute] = [[kCTFontOpenTypeFeatureTag: "tnum", kCTFontOpenTypeFeatureValue: 1]]
    }
    if r.font == "dm" {
        attrs[kCTFontVariationAttribute] = [tag("opsz"): min(40, max(9, r.size)), tag("wght"): r.weight]
        let d = CTFontDescriptorCreateCopyWithAttributes(dmBase, attrs as CFDictionary)
        return CTFontCreateWithFontDescriptor(d, r.size, nil)
    }
    let w: NSFont.Weight = switch r.weight {
    case ..<450: .regular
    case ..<550: .medium
    case ..<650: .semibold
    case ..<750: .bold
    default: .heavy
    }
    let sys = NSFont.systemFont(ofSize: r.size, weight: w) as CTFont
    if attrs.isEmpty { return sys }
    return CTFontCreateCopyWithAttributes(sys, r.size, nil, CTFontDescriptorCreateWithAttributes(attrs as CFDictionary))
}

struct Contour { var v: [[Double]] = [], i: [[Double]] = [], o: [[Double]] = [] }

func contours(of path: CGPath) -> [Contour] {
    var out: [Contour] = []
    var cur = Contour()
    var last = CGPoint.zero
    func p(_ q: CGPoint) -> [Double] { [Double(q.x), Double(q.y)] }
    func add(_ q: CGPoint, inT: CGPoint) {
        cur.v.append(p(q)); cur.i.append([Double(inT.x - q.x), Double(inT.y - q.y)]); cur.o.append([0, 0])
        last = q
    }
    func finish() {
        guard cur.v.count > 1 else { cur = Contour(); return }
        // A contour that ends on its start point: fold the end into the start.
        if let f = cur.v.first, let l = cur.v.last, abs(f[0] - l[0]) < 1e-6, abs(f[1] - l[1]) < 1e-6 {
            cur.i[0] = cur.i.removeLast(); cur.v.removeLast(); cur.o.removeLast()
        }
        out.append(cur); cur = Contour()
    }
    path.applyWithBlock { e in
        let el = e.pointee, pts = el.points
        switch el.type {
        case .moveToPoint:
            finish(); add(pts[0], inT: pts[0])
        case .addLineToPoint:
            add(pts[0], inT: pts[0])
        case .addQuadCurveToPoint:
            let c = pts[0], q = pts[1]
            let c1 = CGPoint(x: last.x + 2 / 3 * (c.x - last.x), y: last.y + 2 / 3 * (c.y - last.y))
            let c2 = CGPoint(x: q.x + 2 / 3 * (c.x - q.x), y: q.y + 2 / 3 * (c.y - q.y))
            cur.o[cur.o.count - 1] = [Double(c1.x - last.x), Double(c1.y - last.y)]
            add(q, inT: c2)
        case .addCurveToPoint:
            cur.o[cur.o.count - 1] = [Double(pts[0].x - last.x), Double(pts[0].y - last.y)]
            add(pts[2], inT: pts[1])
        case .closeSubpath:
            finish()
        @unknown default: break
        }
    }
    finish()
    return out
}

func r3(_ x: Double) -> Double { (x * 1000).rounded() / 1000 }

let reqs = try JSONDecoder().decode([Req].self, from: FileHandle.standardInput.readDataToEndOfFile())
var result: [String: Any] = [:]
for r in reqs {
    let f = font(r)
    var attrs: [NSAttributedString.Key: Any] = [.font: f]
    if let t = r.tracking { attrs[.kern] = t }
    let line = CTLineCreateWithAttributedString(NSAttributedString(string: r.text, attributes: attrs))
    var cs: [[String: Any]] = []
    for run in CTLineGetGlyphRuns(line) as! [CTRun] {
        let runFont = (CTRunGetAttributes(run) as NSDictionary)[kCTFontAttributeName] as! CTFont
        let n = CTRunGetGlyphCount(run)
        var glyphs = [CGGlyph](repeating: 0, count: n), pos = [CGPoint](repeating: .zero, count: n)
        CTRunGetGlyphs(run, CFRange(location: 0, length: n), &glyphs)
        CTRunGetPositions(run, CFRange(location: 0, length: n), &pos)
        for k in 0..<n {
            var t = CGAffineTransform(a: 1, b: 0, c: 0, d: -1, tx: pos[k].x, ty: -pos[k].y)
            guard let gp = CTFontCreatePathForGlyph(runFont, glyphs[k], &t) else { continue }
            for c in contours(of: gp) {
                cs.append(["v": c.v.map { $0.map(r3) }, "i": c.i.map { $0.map(r3) }, "o": c.o.map { $0.map(r3) }])
            }
        }
    }
    result[r.id] = [
        "width": Double(CTLineGetTypographicBounds(line, nil, nil, nil)) - (r.tracking ?? 0),
        "ascent": Double(CTFontGetAscent(f)), "descent": Double(CTFontGetDescent(f)), "leading": Double(CTFontGetLeading(f)),
        "contours": cs,
    ]
}
FileHandle.standardOutput.write(try JSONSerialization.data(withJSONObject: result))
