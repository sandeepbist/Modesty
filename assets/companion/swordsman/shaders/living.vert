#version 440
layout(location=0) in vec4 qt_Vertex;
layout(location=1) in vec2 qt_MultiTexCoord0;
layout(location=0) out vec2 texCoord;
layout(std140,binding=0) uniform buf {
    mat4 qt_Matrix;
    float qt_Opacity;
    float phase;
    float energy;
    vec4 frameRect;
    vec2 spriteSize;
    vec4 previousRect;
    float blend;
    vec4 currentBounds;
    vec4 previousBounds;
};
void main() {
    texCoord=qt_MultiTexCoord0;
    vec2 uv=clamp((texCoord-currentBounds.xy)/currentBounds.zw,vec2(0.0),vec2(1.0));
    vec4 p=qt_Vertex;
    // Gentle local cloth/hair movement, with the hips fixed to the ledge.
    float hair=(1.0-smoothstep(0.13,0.39,uv.y));
    float scarf=smoothstep(0.60,0.90,uv.x)*smoothstep(0.30,0.44,uv.y)*(1.0-smoothstep(0.52,0.65,uv.y));
    p.x+=sin(phase+uv.y*3.0)*hair*0.006*spriteSize.x*energy;
    p.y+=sin(phase*2.0-uv.x*4.0)*scarf*0.022*spriteSize.y*energy;
    float boots=smoothstep(0.78,0.94,uv.y);
    p.x+=sin(phase+uv.x*5.0)*boots*0.005*spriteSize.x*energy;
    gl_Position=qt_Matrix*p;
}
