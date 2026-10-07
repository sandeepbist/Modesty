.pragma library

// Small, escaped Markdown subset. Never accept model-supplied HTML or images.
function escape(text) {
    return String(text).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;").replace(/'/g,"&#39;");
}
function safeLink(url) {return /^https?:\/\/[^\s<>"']+$/i.test(url);}
function inline(text, accent, depth) {
    if((depth||0)>2)return escape(text);
    const pattern=/`([^`\n]+)`|\*\*([^*\n]+)\*\*|\*([^*\n]+)\*|\[([^\]\n]+)\]\(([^\s)]+)\)/g;
    let result="",from=0,match;
    while((match=pattern.exec(text))!==null){
        result+=escape(text.slice(from,match.index));
        if(match[1])result+="<code>"+escape(match[1])+"</code>";
        else if(match[2])result+="<b>"+inline(match[2],accent,(depth||0)+1)+"</b>";
        else if(match[3])result+="<i>"+escape(match[3])+"</i>";
        else result+=safeLink(match[5])?"<a style='color:"+escape(accent)+"' href='"+escape(match[5])+"'>"+escape(match[4])+"</a>":escape(match[0]);
        from=pattern.lastIndex;
    }
    return result+escape(text.slice(from));
}
function prose(text, accent, leading) {
    const lines=text.split("\n"),result=[];
    let paragraph=[],list="";
    function flush(){if(paragraph.length){result.push("<p style='margin:0 0 10px 0;line-height:"+leading+"%'>"+paragraph.map(line=>inline(line,accent)).join("<br>")+"</p>");paragraph=[];}}
    function closeList(){if(list){result.push("</"+list+">");list="";}}
    for(const line of lines){
        const heading=/^#{1,4}\s+(.+)$/.exec(line),bullet=/^\s*(?:[-*+]\s+|\d+[.)]\s+)(.+)$/.exec(line);
        if(!line.trim()){flush();closeList();continue;}
        if(heading){flush();closeList();result.push("<p style='margin:8px 0;font-weight:600'>"+inline(heading[1],accent)+"</p>");}
        else if(bullet){flush();const kind=/^\s*\d/.test(line)?"ol":"ul";if(list!==kind){closeList();list=kind;result.push("<"+kind+" style='margin-top:0;margin-bottom:10px;margin-left:20px'>");}result.push("<li style='line-height:"+leading+"%'>"+inline(bullet[1],accent)+"</li>");}
        else{closeList();paragraph.push(line);}
    }
    flush();closeList();return result.join("");
}
function blocks(text) {
    const result=[];let body=[],language="",code=false;
    function flush(){if(body.length){result.push({key:String(result.length)+(code?"code":"prose"),kind:code?"code":"prose",body:body.join("\n"),language});body=[];}}
    for(const line of text.replace(/\r\n/g,"\n").split("\n")){
        const fence=/^\s*```([\w+.-]*)\s*$/.exec(line);
        if(fence){flush();code=!code;language=code?fence[1]:"";}
        else body.push(line);
    }
    flush();return result.filter(block=>block.kind==="code"||block.body.trim());
}
