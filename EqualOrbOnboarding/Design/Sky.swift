import SwiftUI

/// The background behind every onboarding screen. Restrained on purpose: white, lit by three large,
/// soft pools of Equal's greens (emerald behind the orb, lime low on the left, teal on the right)
/// that drift and breathe slowly, with a fine film grain that keeps the colour from looking flat or
/// digital. Equal's doodles sit over the top, fading out by the middle of the screen.
///
/// Accessibility: Reduce Motion freezes it; Reduce Transparency or Increase Contrast leaves
/// plain white.
struct Sky: View {
    @Environment(\.accessibilityReduceTransparency) private var reduceTransparency
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @Environment(\.colorSchemeContrast) private var contrast

    private var plain: Bool { reduceTransparency || contrast == .increased }

    var body: some View {
        GeometryReader { g in
            ZStack(alignment: .top) {
                Color.white
                if !plain {
                    TimelineView(.animation(minimumInterval: 1 / 30, paused: reduceMotion)) { tl in
                        Spotlight(t: tl.date.timeIntervalSinceReferenceDate, size: g.size)
                    }
                    Grain().opacity(0.9)
                    doodles(g.size)
                }
            }
        }
        .ignoresSafeArea()
        .allowsHitTesting(false)
        .accessibilityHidden(true)
    }

    /// Equal's doodle pattern: clearly there at the top, fading to nothing by the middle.
    private func doodles(_ size: CGSize) -> some View {
        Image("Doodles")
            .renderingMode(.template)
            .foregroundStyle(Color(hex: 0x0B4A30).opacity(0.09))
            .frame(width: size.width, height: size.height * 0.6, alignment: .top)
            .clipped()
            .mask {
                LinearGradient(stops: [
                    .init(color: .black, location: 0),
                    .init(color: .black.opacity(0.6), location: 0.35),
                    .init(color: .clear, location: 1)
                ], startPoint: .top, endPoint: .bottom)
            }
    }
}

private func wave(_ t: Double, _ period: Double, _ phase: Double) -> Double {
    sin(t / period * 2 * .pi + phase)
}

// MARK: - Spotlight

/// Large, smooth pools of light on white, drifting and breathing slowly.
private struct Spotlight: View {
    var t: Double
    var size: CGSize

    private struct Pool { var color: UInt32; var alpha, x, y, r, drift, period, phase: Double }
    private static let pools: [Pool] = [
        Pool(color: 0x22C76A, alpha: 0.20, x: 0.55, y: 0.30, r: 0.95, drift: 0.10, period: 18, phase: 0),
        Pool(color: 0xB9EE5A, alpha: 0.22, x: 0.05, y: 0.85, r: 0.90, drift: 0.12, period: 22, phase: 2),
        Pool(color: 0x4FD6B8, alpha: 0.16, x: 1.00, y: 0.60, r: 0.85, drift: 0.12, period: 20, phase: 4)
    ]

    var body: some View {
        ZStack {
            ForEach(Self.pools.indices, id: \.self) { i in
                let p = Self.pools[i]
                let r = size.width * p.r * (1 + 0.08 * wave(t, p.period * 0.7, p.phase))
                RadialGradient(colors: [Color(hex: p.color).opacity(p.alpha), Color(hex: p.color).opacity(0)],
                               center: .center, startRadius: 0, endRadius: r)
                    .frame(width: r * 2, height: r * 2)
                    .position(x: size.width * (p.x + p.drift * wave(t, p.period, p.phase)),
                              y: size.height * p.y + size.width * p.drift * wave(t, p.period * 1.3, p.phase + 1))
            }
        }
        .frame(width: size.width, height: size.height)
    }
}

// MARK: - Grain

/// Fine film grain, drawn once: tiny light and dark specks that give the colour a printed,
/// tactile finish.
private struct Grain: View {
    var body: some View {
        Canvas(rendersAsynchronously: true) { ctx, size in
            var rng = SplitMix(seed: 7)
            let count = Int(size.width * size.height / 9)
            for _ in 0..<count {
                let x = Double(rng.next() % 10_000) / 10_000 * size.width
                let y = Double(rng.next() % 10_000) / 10_000 * size.height
                let dark = rng.next() % 2 == 0
                ctx.fill(Path(CGRect(x: x, y: y, width: 0.8, height: 0.8)),
                         with: .color(dark ? Color.black.opacity(0.05) : Color.white.opacity(0.5)))
            }
        }
        .drawingGroup()
    }
}

private struct SplitMix {
    var state: UInt64
    init(seed: UInt64) { state = seed }
    mutating func next() -> UInt64 {
        state &+= 0x9E3779B97F4A7C15
        var z = state
        z = (z ^ (z >> 30)) &* 0xBF58476D1CE4E5B9
        z = (z ^ (z >> 27)) &* 0x94D049BB133111EB
        return z ^ (z >> 31)
    }
}
