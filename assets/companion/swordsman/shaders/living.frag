#version 440
layout(location=0) in vec2 texCoord;
layout(location=0) out vec4 fragColor;
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
layout(binding=1) uniform sampler2D atlas;
layout(binding=2) uniform sampler2D previousAtlas;
void main(){
    vec2 uv=(texCoord-currentBounds.xy)/currentBounds.zw;
    vec2 oldUV=(texCoord-previousBounds.xy)/previousBounds.zw;
    // Sample outside divergent branches so mipmap derivatives remain valid at
    // the sprite edges. Branching here creates bright rectangular seams.
    vec4 current=texture(atlas,frameRect.xy+uv*frameRect.zw);
    vec4 previous=texture(previousAtlas,previousRect.xy+oldUV*previousRect.zw);
    current*=step(0.0,uv.x)*step(uv.x,1.0)*step(0.0,uv.y)*step(uv.y,1.0);
    previous*=step(0.0,oldUV.x)*step(oldUV.x,1.0)*step(0.0,oldUV.y)*step(oldUV.y,1.0);
    fragColor=mix(previous,current,blend)*qt_Opacity;
}
