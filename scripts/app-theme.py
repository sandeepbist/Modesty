#!/usr/bin/env python3
"""Generate managed application colors through Matugen's template engine."""
import json, os, re, shutil, subprocess, stat, configparser, importlib.util, hashlib
import folder_theme
from pathlib import Path

CONFIG=Path(os.environ.get('XDG_CONFIG_HOME',Path.home()/'.config'))

def backup(path,state):
    if path.exists():
        dest=state/'theme-backups'/str(path.relative_to(CONFIG))
        if not dest.exists():dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,dest)

def write(path,text):
    path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_name(path.name+'.modesty-tmp');temp.write_text(text);temp.replace(path)

def integrate(path,line,state,enabled):
    old=path.read_text() if path.exists() else ''
    clean='\n'.join(x for x in old.splitlines() if 'modesty-generated' not in x)
    if enabled:clean=(line+'\n'+clean) if line.startswith('include=') else clean+'\n'+line
    if clean.strip()!=old.strip():backup(path,state);write(path,clean.strip()+'\n')

def gtk_value(record,key,current,value,enabled):
    previous=record.get(key)
    owned=previous and current in (previous['applied'],previous.get('previous',previous['applied']))
    if enabled:
        original=previous['original'] if owned else current
        record[key]={'original':original,'applied':value}
        if owned and current!=value:record[key]['previous']=current
        return value
    return previous['original'] if owned else current

def complete_gtk_receipt(receipt,record,enabled,keys):
    if not enabled:
        receipt.unlink()
    elif any('previous' in record[key] for key in keys):
        for key in keys:record[key].pop('previous',None)
        write(receipt,json.dumps(record))

def gtk_settings(path,state,mode,enabled):
    receipt=state/'gtk-settings'/(path.parent.name+'.json')
    if not enabled and not receipt.exists():return
    record=json.loads(receipt.read_text()) if receipt.exists() else {}
    old=path.read_text() if path.exists() else ''
    parser=configparser.ConfigParser(interpolation=None);parser.read_string(old)
    values={'gtk-application-prefer-dark-theme':'1' if mode=='dark' else '0'}
    theme='adw-gtk3-dark' if mode=='dark' else 'adw-gtk3'
    if (Path('/usr/share/themes')/theme).exists():values['gtk-theme-name']=theme
    changes={}
    for key in values if enabled else list(record):
        current=parser.get('Settings',key,fallback=None)
        value=gtk_value(record,key,current,values.get(key),enabled)
        if value!=current:changes[key]=value
    if enabled:write(receipt,json.dumps(record))
    if changes:
        section=re.search(r'(?m)^[ \t]*\[Settings\][^\r\n]*(?:\r?\n|$)',old)
        start=section.end() if section else len(old)
        end=re.search(r'(?m)^[ \t]*\[',old[start:])
        end=start+end.start() if end else len(old)
        body=old[start:end]
        for key,value in changes.items():
            pattern=re.compile(r'^([ \t]*'+re.escape(key)+r'[ \t]*[=:][ \t]*)[^\r\n]*(\r?\n|$)',re.M|re.I)
            if pattern.search(body):
                body=pattern.sub(lambda match:match[1]+value+match[2] if value is not None else '',body)
            elif value is not None:
                body+=('' if not body or body.endswith('\n') else '\n')+key+'='+value+'\n'
        prefix=old[:start]
        if not section:prefix+=('' if not prefix or prefix.endswith('\n') else '\n')+'[Settings]\n'
        elif prefix and not prefix.endswith('\n'):prefix+='\n'
        backup(path,state);write(path,prefix+body+old[end:])
    complete_gtk_receipt(receipt,record,enabled,values)

def gtk_import(path,state,enabled):
    old=path.read_text() if path.exists() else ''
    clean=re.sub(r'''(?m)^[ \t]*@import[ \t]+["']modesty-generated\.css["'][ \t]*;[ \t]*(?:\r?\n|$)''','',old)
    new='@import "modesty-generated.css";\n'+clean if enabled else clean
    if new!=old:backup(path,state);write(path,new)

def migrate_thunar(path,state):
    # Migrate only unchanged bundled versions; preserve user-edited CSS.
    # OTA preserves application configs, including users' own CSS changes.
    if not path.is_symlink() and path.exists() and hashlib.sha256(path.read_bytes()).hexdigest() in {'06f3268dbda4afead19facbbc10bc4276323a49707c9d14fc0e77beeec0452aa','c54aacc5240c3467a9653fc1f49c83893895592f19a6ec85e85755a3af2bc3e4','58df7b6b5e5b9a1a2c7de5d426782a00b01c46bce4c62c0ac90f9c899c7bd5af','d416067c81f6762ce3391af2fb1dff7a356157a81ebb2c98de35189300ca8774'}:
        backup(path,state)
        write(path,(Path(__file__).resolve().parents[1]/'setup/config/gtk-3.0/thunar.css').read_text())

def terminal_colors(raw,mode):
    # Preserve ANSI semantics: magenta and cyan must not reuse green/yellow.
    dark=['24262e','f07886','9bdc91','edca80','91b9ff','d4a0ed','78cfd6','e6e8ef',
          '8b93a5','ff9ba5','b4edac','ffe0a3','b0cfff','e5b9fa','9ae7eb','ffffff']
    light=['252934','ac263b','286c39','805800','285ea6','894395','096d77','525b6b',
           '646d7d','bc2f47','347a43','8c650b','356db7','9951a5','147d87','20242d']
    values=dark if mode=='dark' else light
    for i,value in enumerate(values):raw['colors']['term'+str(i)]={'default':{'color':'#'+value}}


def apply_live_terminals(raw,state):
    def color(role):
        value=raw['colors'][role]['default']['color']
        if not re.fullmatch(r'#[0-9a-fA-F]{6}',value):raise ValueError('Invalid terminal color')
        return value[1:]
    def osc(role,*codes):
        value=color(role)
        return '\x1b]'+ ';'.join(map(str,codes))+';rgb:'+ '/'.join(value[i:i+2] for i in (0,2,4))+'\x1b\\'
    sequence=''.join(osc(role,code) for role,code in [('on_surface',10),('surface',11),('primary',12),('primary',17),('on_primary',19)])
    sequence+=''.join(osc('term'+str(index),4,index) for index in range(16))
    sequence+=''.join(osc(role,4,index) for index,role in enumerate(['primary','secondary','tertiary'],16))
    write(state/'sequences.txt',sequence)
    processes={}
    for path in Path('/proc').iterdir():
        if not path.name.isdigit():continue
        try:
            if path.stat().st_uid!=os.getuid():continue
            data=(path/'stat').read_text(); end=data.rfind(')')
            processes[int(path.name)]=(int(data[end+2:].split()[1]),data[data.index('(')+1:end])
        except (OSError,ValueError,IndexError):continue
    terminals=set()
    for pid in processes:
        ancestor=pid; seen=set()
        while ancestor in processes and ancestor not in seen:
            seen.add(ancestor);parent,comm=processes[ancestor]
            managed=comm=='foot'
            if comm=='kitty':
                try:managed=str(CONFIG/'kitty/modesty.conf').encode() in Path(f'/proc/{ancestor}/cmdline').read_bytes().split(b'\0')
                except OSError:pass
            if managed:
                try:
                    tty=os.readlink(f'/proc/{pid}/fd/0')
                    if re.fullmatch(r'/dev/pts/\d+',tty):terminals.add(tty)
                except OSError:pass
                break
            ancestor=parent
    for tty in terminals:
        try:
            fd=os.open(tty,os.O_WRONLY|os.O_NONBLOCK|os.O_NOCTTY|os.O_NOFOLLOW)
            try:
                info=os.fstat(fd)
                if info.st_uid==os.getuid() and stat.S_ISCHR(info.st_mode):os.write(fd,sequence.encode())
            finally:os.close(fd)
        except OSError:pass


def apply(raw,mode,state,targets):
    # JSON subcommand uses supplied defaults; remap them explicitly for light mode.
    raw=json.loads(json.dumps(raw))
    for value in raw['colors'].values():
        if mode in value:value['default']=value[mode]
    raw['mode']=mode;raw['is_dark_mode']=mode=='dark'
    if targets.get('spotify'):
        spec=importlib.util.spec_from_file_location('spotify_theme',Path(__file__).with_name('spotify-theme.py'))
        spotify=importlib.util.module_from_spec(spec);spec.loader.exec_module(spotify)
        spotify.apply(raw,mode)
    terminal_colors(raw,mode)
    generated=state/'matugen';generated.mkdir(parents=True,exist_ok=True)
    source=generated/'input.json';write(source,json.dumps(raw))
    def color(name):return '{{colors.'+name+'.default.hex}}'
    gtk='/* Modesty generated palette */\n'
    names={'accent_color':'primary','accent_bg_color':'primary','accent_fg_color':'on_primary','window_bg_color':'surface','window_fg_color':'on_surface','view_bg_color':'surface_container_lowest','view_fg_color':'on_surface','headerbar_bg_color':'surface_container','headerbar_fg_color':'on_surface','popover_bg_color':'surface_container','popover_fg_color':'on_surface','card_bg_color':'surface_container','card_fg_color':'on_surface','sidebar_bg_color':'surface_container_low','sidebar_fg_color':'on_surface','theme_bg_color':'surface','theme_fg_color':'on_surface','theme_base_color':'surface_container_lowest','theme_text_color':'on_surface','theme_selected_fg_color':'on_surface','primary':'primary','error_color':'error'}
    for name,role in names.items():gtk+='@define-color '+name+' '+color(role)+';\n'
    # Thunar's highlighted icon cells paint these named colors directly.
    # Widget background CSS alone cannot change that renderer.
    for name in ('theme_selected_bg_color','theme_unfocused_selected_bg_color'):
        gtk+='@define-color '+name+' alpha('+color('primary')+', 0.18);\n'
    foot='initial-color-theme='+mode+'\n'
    for section in ('colors-dark','colors-light'):
        foot+='['+section+']\n'
        for key,role in {'background':'surface','foreground':'on_surface','selection-background':'primary','selection-foreground':'on_primary','urls':'primary'}.items():foot+=key+'={{colors.'+role+'.default.hex_stripped}}\n'
        for prefix in ('regular','bright'):
            for i in range(8):foot+=prefix+str(i)+'={{colors.term'+str(i+(8 if prefix=='bright' else 0))+'.default.hex_stripped}}\n'
    kitty='\n'.join(key+' '+color(role) for key,role in {
        'background':'surface','foreground':'on_surface','cursor':'primary',
        'cursor_text_color':'on_primary','selection_background':'primary',
        'selection_foreground':'on_primary','url_color':'primary'}.items())+'\n'
    kitty+='\n'.join('color'+str(i)+' '+color('term'+str(i)) for i in range(16))+'\n'
    roles=['on_surface','surface_container','surface_container_highest','surface_container_high','outline','outline_variant','on_surface','on_surface','on_surface','surface_container_lowest','surface','shadow','primary','on_primary','primary','tertiary','surface_container','shadow','surface_container','on_surface','outline','primary']
    qt='[ColorScheme]\n'+'\n'.join(group+'='+', '.join(color(r if group!='disabled_colors' or r!='on_surface' else 'outline') for r in roles) for group in ['active_colors','inactive_colors','disabled_colors'])+'\n'
    files={'gtk':('gtk.css',gtk),'foot':('foot.ini',foot),'kitty':('kitty.conf',kitty),'qt':('qt.conf',qt)}
    config='[config]\n'
    for key,(filename,template) in files.items():
        template_path=generated/(filename+'.template');write(template_path,template)
        config+='\n[templates.'+key+']\ninput_path = '+json.dumps(str(template_path))+'\noutput_path = '+json.dumps(str(generated/filename))+'\n'
    config_path=generated/'config.toml';write(config_path,config)
    subprocess.run(['matugen','json',str(source),'--config',str(config_path),'--mode',mode],check=True,capture_output=True,text=True,timeout=8)
    for version in ('3.0','4.0'):
        css=CONFIG/('gtk-'+version)/'gtk.css'
        target=css.parent/'modesty-generated.css'
        if targets.get('gtk'):write(target,(generated/'gtk.css').read_text())
        if targets.get('gtk'):
            migrate_thunar(css.parent/'thunar.css',state)
        gtk_import(css,state,bool(targets.get('gtk')))
        gtk_settings(css.parent/'settings.ini',state,mode,bool(targets.get('gtk')))
    foot_config=CONFIG/'foot'/'foot.ini'
    if foot_config.exists():
        target=foot_config.parent/'modesty-generated.ini'
        if targets.get('foot'):
            write(target,(generated/'foot.ini').read_text())
        integrate(foot_config,'include='+str(target),state,targets.get('foot',False))
    kitty_config=CONFIG/'kitty'/'modesty.conf'
    if kitty_config.exists():
        target=kitty_config.parent/'modesty-generated.conf'
        if targets.get('foot'):write(target,(generated/'kitty.conf').read_text())
        integrate(kitty_config,'include '+str(target),state,targets.get('foot',False))
    if targets.get('foot') and (foot_config.exists() or kitty_config.exists()):
        apply_live_terminals(raw,state)
    qt_config=CONFIG/'qt6ct'/'qt6ct.conf'
    if qt_config.exists():
        old=qt_config.read_text();backup(qt_config,state)
        target=qt_config.parent/'colors'/'modesty-generated.conf'
        if targets.get('qt'):
            write(target,(generated/'qt.conf').read_text())
            new=re.sub(r'^color_scheme_path=.*$', 'color_scheme_path='+str(target),old,flags=re.M)
            new=re.sub(r'^custom_palette=.*$', 'custom_palette=true',new,flags=re.M)
            write(qt_config,new)
        elif 'modesty-generated.conf' in old:
            original=state/'theme-backups'/'qt6ct'/'qt6ct.conf'
            original=original.read_text() if original.exists() else ''
            for key in ('color_scheme_path','custom_palette'):
                match=re.search(r'^'+key+r'=.*$',original,re.M)
                if match:old=re.sub(r'^'+key+r'=.*$',lambda _:match.group(),old,flags=re.M)
            write(qt_config,old)
    folder_theme.apply(raw,state,bool(targets.get('gtk') and targets.get('folders')))
