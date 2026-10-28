#version 440
layout(location = 0) in vec2 qt_TexCoord0;
layout(location = 0) out vec4 fragColor;
layout(std140, binding = 0) uniform buf {
    mat4 qt_Matrix;
    float qt_Opacity;
    vec2 extent;
    vec4 shapeA;
    vec4 shapeB;
    vec4 shapeC;
    vec3 radii;
    vec3 alphas;
    vec4 fillColor;
    vec4 edgeColor;
    float shadowEnabled;
    float mergeProgress;
};
float distanceTo(vec2 p, vec4 box, float radius) {
    vec2 halfSize = box.zw * .5;
    float r = min(radius, min(halfSize.x, halfSize.y));
    vec2 q = abs(p - box.xy - halfSize) - halfSize + r;
    return length(max(q, 0.0)) + min(max(q.x, q.y), 0.0) - r;
}

float pairDistance(vec2 p, vec4 a, vec4 b, float ra, float rb) {
    float da=distanceTo(p,a,ra), db=distanceTo(p,b,rb);
    vec4 delta=vec4(a.xy-b.xy,(b.xy+b.zw)-(a.xy+a.zw));
    float exposure=max(0.0,min(max(max(delta.x,delta.y),max(delta.z,delta.w)),max(max(-delta.x,-delta.y),max(-delta.z,-delta.w))));
    float k=min(ra,rb)*1.6*smoothstep(0.0,min(ra,rb)*.5,exposure)*smoothstep(0.0,.18,mergeProgress);
    vec2 lo=min(a.xy,b.xy), hi=max(a.xy+a.zw,b.xy+b.zw);
    vec2 room=max(vec2(da,db)-distanceTo(p,vec4(lo,hi-lo),min(ra,rb)),vec2(0.0));
    float limit=room.x+room.y+2.0*sqrt(room.x*room.y);
    k*=limit/max(k+limit,.0001);
    float h=max(k-abs(da-db),0.0)/max(k,.0001);
    return min(da,db)-k*h*h*.25;
}
float field(vec2 p, float inset, float aa, bool shadow) {
    vec3 d=vec3(distanceTo(p,shapeA,radii.x),distanceTo(p,shapeB,radii.y),distanceTo(p,shapeC,radii.z));
    vec3 pairs=vec3(pairDistance(p,shapeA,shapeB,radii.x,radii.y),pairDistance(p,shapeA,shapeC,radii.x,radii.z),pairDistance(p,shapeB,shapeC,radii.y,radii.z));
    vec3 pairAlpha=vec3(min(alphas.x,alphas.y),min(alphas.x,alphas.z),min(alphas.y,alphas.z));
    vec3 v=shadow?exp(-pow(max(d,0.0),vec3(2.0))/32.0)*alphas:(1.0-smoothstep(vec3(-aa),vec3(aa),d+inset))*alphas;
    vec3 w=shadow?exp(-pow(max(pairs,0.0),vec3(2.0))/32.0)*pairAlpha:(1.0-smoothstep(vec3(-aa),vec3(aa),pairs+inset))*pairAlpha;
    return max(max(v.x,max(v.y,v.z)),max(w.x,max(w.y,w.z)));
}
void main() {
    vec2 p=qt_TexCoord0*extent;
    float aa=max(.45,fwidth(p.x)*.65);
    float coverage=field(p,0.0,aa,false), inset=field(p,1.0,aa,false);
    float edge=max(0.0,coverage-inset);
    float shadow=field(p-vec2(0,3),0.0,aa,true)*.22*shadowEnabled;
    float alpha=coverage*fillColor.a+edge*edgeColor.a*(1.0-fillColor.a);
    vec3 rgb=fillColor.rgb*coverage*fillColor.a;
    rgb=mix(rgb,edgeColor.rgb*coverage,edge*edgeColor.a);
    fragColor=vec4(rgb,alpha+shadow*(1.0-alpha))*qt_Opacity;
}
