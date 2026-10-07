#!/usr/bin/env python3
"""Bounded, on-demand Qalculate evaluation for the launcher."""
import json, os, re, subprocess, sys, tempfile

def calculate(query):
    expression=query.strip().removeprefix('=').strip()
    if not expression or len(expression)>300:
        return {'query':query,'result':'','error':''}
    if re.search(r'[+*/^=,-]$',expression):
        return {'query':query,'result':'','error':'Finish the expression.'}
    # This field evaluates mathematics, never qalc commands or file functions.
    if re.search(r'[\n\r"\'`\\]|:=|\b(?:save|store|export|import|load|plot|command|system|function|variable|delete|exrates)\b',expression,re.I):
        return {'query':query,'result':'','error':'Enter a mathematical expression.'}
    with tempfile.TemporaryDirectory(prefix='modesty-qalc-') as config:
        result=subprocess.run(['qalc','-t','-defaults','-m','700','-s','upxrates 0','-s','autoconversion 0','--',expression],
            stdin=subprocess.DEVNULL,capture_output=True,text=True,timeout=2,
            env=dict(os.environ,XDG_CONFIG_HOME=config,LC_ALL='C.UTF-8',NO_COLOR='1'))
    value=result.stdout.strip()
    error=result.stderr.strip()
    if result.returncode or error or not value or len(value)>1500 or 'error:' in value.lower():
        return {'query':query,'result':'','error':'Check the expression or finish typing.'}
    return {'query':query,'result':value,'error':''}

if __name__=='__main__':
    try: print(json.dumps(calculate(sys.argv[1])),flush=True)
    except FileNotFoundError: print(json.dumps({'query':sys.argv[1],'result':'','error':'Install libqalculate to enable calculations.'}))
    except subprocess.TimeoutExpired: print(json.dumps({'query':sys.argv[1],'result':'','error':'This calculation took too long.'}))
