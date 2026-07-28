"""Color audit: colorblind-safety + WCAG contrast (TASKS H-02, H-06).

Simulates protanopia and deuteranopia with the Machado et al. (2009)
severity-1.0 matrices in linear RGB, then reports pairwise CIE76 ΔE between
the simulated categorical colors (ΔE > 20 reads as clearly distinct).
Also reports WCAG 2.1 contrast ratios for every text/background pair the
stylesheet uses.

    uv run python tools/audit_colors.py
"""

from __future__ import annotations

# Machado, Oliveira & Fernandes (2009), severity 1.0.
PROTANOPIA = [
    (0.152286, 1.052583, -0.204868),
    (0.114503, 0.786281, 0.099216),
    (-0.003882, -0.048116, 1.051998),
]
DEUTERANOPIA = [
    (0.367322, 0.860646, -0.227968),
    (0.280085, 0.672501, 0.047413),
    (-0.011820, 0.042940, 0.968881),
]

CHART = {
    "Mythology": "#56B4E9",
    "Monster-of-the-Week": "#E69F00",
    "Standalone": "#009E73",
}
TEXT_PAIRS = [
    ("body text", "#f1f5f2", "#111417"),
    ("muted text", "#9aa8a0", "#111417"),
    ("links", "#8fc7ff", "#111417"),
    ("lede", "#cbd6cf", "#111417"),
    ("footer", "#aeb9b2", "#111417"),
    ("table header", "#f1f5f2", "#1a2019"),
    ("contested badge", "#f2b84b", "#111417"),
    ("accent", "#7fd4a0", "#111417"),
]


def _hex_to_rgb(value: str) -> tuple[float, ...]:
    value = value.lstrip("#")
    return tuple(int(value[i : i + 2], 16) / 255 for i in (0, 2, 4))


def _to_linear(channel: float) -> float:
    if channel <= 0.04045:
        return channel / 12.92
    return ((channel + 0.055) / 1.055) ** 2.4


def _simulate(hex_color: str, matrix) -> tuple[float, ...]:
    linear = tuple(_to_linear(c) for c in _hex_to_rgb(hex_color))
    return tuple(
        max(0.0, min(1.0, sum(row[i] * linear[i] for i in range(3)))) for row in matrix
    )


def _linear_to_lab(rgb: tuple[float, float, float]) -> tuple[float, float, float]:
    r, g, b = rgb
    x = (0.4124 * r + 0.3576 * g + 0.1805 * b) / 0.95047
    y = 0.2126 * r + 0.7152 * g + 0.0722 * b
    z = (0.0193 * r + 0.1192 * g + 0.9505 * b) / 1.08883

    def f(t: float) -> float:
        return t ** (1 / 3) if t > 0.008856 else 7.787 * t + 16 / 116

    fx, fy, fz = f(x), f(y), f(z)
    return 116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)


def _delta_e(a: tuple, b: tuple) -> float:
    la, aa, ba = _linear_to_lab(a)
    lb, ab, bb = _linear_to_lab(b)
    return ((la - lb) ** 2 + (aa - ab) ** 2 + (ba - bb) ** 2) ** 0.5


def _luminance(hex_color: str) -> float:
    r, g, b = (_to_linear(c) for c in _hex_to_rgb(hex_color))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(fg: str, bg: str) -> float:
    lighter, darker = sorted((_luminance(fg), _luminance(bg)), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


def main() -> None:
    names = list(CHART)
    print("== Colorblind simulation (pairwise CIE76 ΔE; >20 = distinct) ==")
    for label, matrix in (("protanopia", PROTANOPIA), ("deuteranopia", DEUTERANOPIA)):
        sims = {name: _simulate(CHART[name], matrix) for name in names}
        for i, a in enumerate(names):
            for b in names[i + 1 :]:
                print(f"  {label:12s} {a} vs {b}: ΔE = {_delta_e(sims[a], sims[b]):.1f}")
    print()
    print("== WCAG contrast (AA: 4.5 normal text, 3.0 large/UI) ==")
    worst: tuple[str, float] = ("", float("inf"))
    for label, fg, bg in TEXT_PAIRS:
        ratio = contrast(fg, bg)
        if ratio < worst[1]:
            worst = (label, ratio)
        print(f"  {label:16s} {fg} on {bg}: {ratio:.2f}:1")
    print(f"\n  lowest: {worst[0]} at {worst[1]:.2f}:1")
    print()
    print("== Chart colors vs page background ==")
    for name in names:
        print(f"  {name:22s} {CHART[name]}: {contrast(CHART[name], '#111417'):.2f}:1")


if __name__ == "__main__":
    main()
