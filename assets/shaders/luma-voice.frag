#version 440
layout(location = 0) in vec2 qt_TexCoord0;
layout(location = 0) out vec4 fragColor;
layout(std140, binding = 0) uniform buf {
    mat4 qt_Matrix;
    float qt_Opacity;
    float phase;
    float revealProgress;
    float summon;
    float energy;
    float mode;
    float edge;
    vec2 extent;
    float radius;
    vec4 primaryColor;
    vec4 secondaryColor;
    vec4 tertiaryColor;
};

const float PI = 3.14159265;

// Clockwise distance around the actual rounded perimeter, starting at top-left.
float perimeterPosition(vec2 position, vec2 straight, vec2 q, float r) {
    float quarter = PI * r * 0.5;
    if (q.x > 0.0 && q.y > 0.0) {
        float angle = atan(q.y, q.x);
        if (position.x >= 0.0 && position.y < 0.0)
            return 2.0 * straight.x + r * (PI * 0.5 - angle);
        if (position.x >= 0.0)
            return 2.0 * straight.x + quarter + 2.0 * straight.y + r * angle;
        if (position.y >= 0.0)
            return 4.0 * straight.x + 2.0 * quarter + 2.0 * straight.y + r * (PI * 0.5 - angle);
        return 4.0 * straight.x + 3.0 * quarter + 4.0 * straight.y + r * angle;
    }
    if (q.y >= q.x) {
        if (position.y < 0.0) return position.x + straight.x;
        return 3.0 * straight.x + 2.0 * quarter + 2.0 * straight.y - position.x;
    }
    if (position.x >= 0.0)
        return 2.0 * straight.x + quarter + position.y + straight.y;
    return 4.0 * straight.x + 3.0 * quarter + 3.0 * straight.y - position.y;
}

float beamAt(float path, float head, float perimeter, float spread) {
    float delta = mod(path - head + perimeter * 0.5, perimeter) - perimeter * 0.5;
    float normalized = delta / max(1.0, spread);
    return exp(-normalized * normalized);
}

void main() {
    if (edge > 0.5) {
        // Border rendering skips all voice-wave calculations below.
        vec2 position = (qt_TexCoord0 - 0.5) * extent;
        vec2 halfSize = extent * 0.5;
        float r = max(0.0, min(radius, min(halfSize.x, halfSize.y)));
        vec2 straight = halfSize - r;
        vec2 q = abs(position) - straight;
        float distance = length(max(q, 0.0)) + min(max(q.x, q.y), 0.0) - r;
        float inside = 1.0 - smoothstep(-0.7, 0.4, distance);
        float rim = exp(-abs(distance + 1.0) * 1.05);
        float wash = exp(-abs(distance) / 8.0);
        vec3 tint;
        float alpha;
        if (summon > 0.5) {
            float progress = clamp(revealProgress, 0.0, 1.0);
            float center = mix(-straight.x, straight.x, progress);
            float offset = (position.x - center) / max(24.0, extent.x * 0.105);
            float beam = exp(-offset * offset);
            float bottom = smoothstep(halfSize.y - max(r, 16.0), halfSize.y - 1.0, position.y);
            float envelope = sin(PI * progress);
            tint = mix(primaryColor.rgb, secondaryColor.rgb, progress * 0.55);
            alpha = inside * bottom * beam * envelope * (rim * 0.78 + wash * 0.16);
        } else {
            float perimeter = max(1.0, 4.0 * (straight.x + straight.y) + 2.0 * PI * r);
            float path = perimeterPosition(position, straight, q, r);
            float head = phase / (2.0 * PI) * perimeter;
            float first = beamAt(path, head, perimeter, perimeter * 0.075);
            float second = beamAt(path, head + perimeter * 0.47, perimeter, perimeter * 0.105);
            float intensity = first + second * 0.62;
            tint = mix(primaryColor.rgb, secondaryColor.rgb, second / max(0.001, first + second) * 0.65);
            alpha = inside * intensity * (rim * (0.58 + energy * 0.18) + wash * (0.08 + energy * 0.04));
        }
        alpha = min(alpha, 1.0);
        fragColor = vec4(tint * alpha, alpha) * qt_Opacity;
        return;
    }

    vec2 p = qt_TexCoord0 * 2.0 - 1.0;
    float working = smoothstep(0.3, 1.0, mode);
    float thinking = smoothstep(1.2, 2.0, mode);
    float acting = smoothstep(2.2, 3.0, mode);
    p.x -= sin(phase) * thinking * 0.12;
    float amplitude = mix(0.035 + energy * 0.42, mix(0.07, 0.16, thinking), working);
    float breath = 0.86 + 0.14 * sin(phase);
    float wave = sin(p.x * 3.5 + phase * 2.0) * amplitude;
    float echo = sin(p.x * 4.8 - phase * 2.0 + 1.4) * amplitude * 0.7;
    float spread = mix(0.045 + energy * 0.065, mix(0.07, 0.11, thinking), working) * breath;
    float envelope = exp(-pow(p.x / mix(0.69 + energy * 0.16, 0.60, working), 4.0));
    envelope *= 1.0 - smoothstep(0.72, 1.0, abs(p.x));
    float first = exp(-pow((p.y - wave) / spread, 2.0));
    float second = exp(-pow((p.y - echo) / (spread * 1.3), 2.0));
    float halo = exp(-pow((p.y - wave * 0.4) / (spread * 3.0), 2.0));
    float hue = 0.5 + 0.5 * sin(p.x * 2.7 + phase);
    vec3 tint = mix(primaryColor.rgb, secondaryColor.rgb, hue * 0.75);
    tint = mix(tint, tertiaryColor.rgb, second * 0.5);
    float core = exp(-pow((p.y - wave) / (spread * 0.34), 2.0));
    float alpha = envelope * (core * (0.38 + energy * 0.30) + first * 0.38 + second * 0.22 + halo * 0.035);

    alpha = min(alpha, 1.0);
    fragColor = vec4(tint * alpha, alpha) * qt_Opacity;
}
