#version 440

layout(location = 0) in vec2 qt_TexCoord0;
layout(location = 0) out vec4 fragColor;

layout(std140, binding = 0) uniform buf {
    mat4 qt_Matrix;
    float qt_Opacity;
    vec4 frostTint;
    vec4 sampleRect;
    vec2 blurStep;
    float glassAmount;
};

layout(binding = 1) uniform sampler2D source;
layout(binding = 2) uniform sampler2D backdrop;

void main() {
    float ink = texture(source, qt_TexCoord0).a;
    if (ink <= 0.0) {
        fragColor = vec4(0.0);
        return;
    }

    vec2 uv = sampleRect.xy + qt_TexCoord0 * sampleRect.zw;
    vec2 dx = vec2(blurStep.x, 0.0);
    vec2 dy = vec2(0.0, blurStep.y);
    vec4 ambient = texture(backdrop, uv) * 0.25
        + (texture(backdrop, uv - dx) + texture(backdrop, uv + dx)
            + texture(backdrop, uv - dy) + texture(backdrop, uv + dy)) * 0.125
        + (texture(backdrop, uv - dx - dy) + texture(backdrop, uv + dx - dy)
            + texture(backdrop, uv - dx + dy) + texture(backdrop, uv + dx + dy)) * 0.0625;

    vec3 blurred = ambient.rgb + frostTint.rgb * (1.0 - ambient.a);
    vec3 fill = mix(frostTint.rgb, blurred, 0.36 * glassAmount);
    float alpha = ink * qt_Opacity * (1.0 - 0.06 * glassAmount);
    fragColor = vec4(fill * alpha, alpha);
}
