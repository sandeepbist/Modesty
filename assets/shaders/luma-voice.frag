#version 440
layout(location = 0) in vec2 qt_TexCoord0;
layout(location = 0) out vec4 fragColor;
layout(std140, binding = 0) uniform buf {
    mat4 qt_Matrix;
    float qt_Opacity;
    float phase;
    float energy;
    float mode;
    float edge;
    vec2 extent;
    float radius;
    vec4 primaryColor;
    vec4 secondaryColor;
    vec4 tertiaryColor;
};

void main() {
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

    if (edge > 0.5) {
        // Rounded distance field: light sits inside the surface, never outside
        // its mask. A diffuse wash follows it without blurring text or children.
        vec2 position = (qt_TexCoord0 - 0.5) * extent;
        vec2 halfSize = extent * 0.5;
        float r = min(radius, min(halfSize.x, halfSize.y));
        vec2 q = abs(position) - halfSize + r;
        float distance = length(max(q, 0.0)) + min(max(q.x, q.y), 0.0) - r;
        float inside = 1.0 - smoothstep(-1.0, 0.5, distance);
        float angle = atan(position.y / max(1.0, halfSize.y - r * 0.5),
                           position.x / max(1.0, halfSize.x - r * 0.5));
        float beam = pow(0.5 + 0.5 * cos(angle - phase), mix(5.0, 11.0, acting));
        float opposite = pow(0.5 + 0.5 * cos(angle - phase + 2.4), 7.0);
        tint = mix(primaryColor.rgb, tertiaryColor.rgb, beam * 0.55);
        tint = mix(tint, secondaryColor.rgb, opposite * 0.45);
        float rim = exp(-abs(distance + 1.2) * 0.70);
        float wash = exp(-abs(distance) / 12.0);
        alpha = inside * (0.90 + 0.10 * sin(phase)) * (rim * (0.055 + beam * (0.32 + energy * 0.16) + opposite * 0.13) + wash * (0.01 + energy * 0.018));
    }
    alpha = min(alpha, 1.0);
    fragColor = vec4(tint * alpha, alpha) * qt_Opacity;
}
