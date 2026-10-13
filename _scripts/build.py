"""
Builds index.html, the HTML port of Pig's Tails, from the original Flash movies

The piece was a frameset: map.swf (820 x 285, 10 fps, 1003 frames, looping) above, and
controls.swf (1100 x 100) below. Both are Flash 1 and nothing in them moves: every shape
and button is placed at one frame and removed at another. So each placement becomes an
element at its original matrix, shown at exactly its frames by a CSS animation of
visibility.

The buttons keep Flash's four states, switched by CSS: up (normally), over (under the
pointer), down (pressed) and hit (the area that takes the pointer, never seen). In map.swf
they have no actions: the patches show under the pointer, or vanish when they are already
laid down. In controls.swf each sends an FSCommand, which controls.htm turned into calls to
the plugin's Zoom() and Pan() on the map; the page does the same with the map's viewBox.

Shapes and the photo are exported by JPEXS FFDec (https://github.com/jindrapetrik/jpexs-decompiler),
which also dumps the movies' tags as XML.

Usage: python3 _scripts/build.py --ffdec /path/to/ffdec-cli.jar
"""
import argparse
import os
import re
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PHOTO = 'photo.jpg'


def ffdec_export(jar, swf, out):
    """the movie's tags as XML, each shape as SVG, and its bitmaps"""
    run = lambda *args: subprocess.run(['java', '-jar', jar, *args], check=True, capture_output=True)
    run('-swf2xml', swf, os.path.join(out, 'movie.xml'))
    run('-format', 'shape:svg', '-export', 'shape', os.path.join(out, 'shapes'), swf)
    run('-export', 'image', os.path.join(out, 'images'), swf)


def matrix(m):
    """a Flash MATRIX as an SVG matrix: x' = a x + c y + e, y' = b x + d y + f"""
    a, d = (float(m.get('scaleX')), float(m.get('scaleY'))) if m.get('hasScale') == 'true' else (1, 1)
    b, c = (float(m.get('rotateSkew0')), float(m.get('rotateSkew1'))) if m.get('hasRotate') == 'true' else (0, 0)
    e, f = int(m.get('translateX')) / 20, int(m.get('translateY')) / 20
    if (a, b, c, d) == (1, 0, 0, 1):
        return f'translate({e:g} {f:g})' if (e, f) != (0, 0) else ''
    return f'matrix({a:g} {b:g} {c:g} {d:g} {e:g} {f:g})'


def fscommand(action_bytes):
    """a button's getURL("FSCommand:command", "args"), as (command, args)"""
    data = bytes.fromhex(action_bytes or '')
    if len(data) > 3 and data[0] == 0x83:
        url, target = data[3:3 + int.from_bytes(data[1:3], 'little')].split(b'\0')[:2]
        url = url.decode('latin-1')
        if url.lower().startswith('fscommand:'):
            return url[10:], target.decode('latin-1')
    return None


def read_movie(xml_path):
    """header, buttons and the placements: each run of a character at a depth, from frame to frame"""
    root = ET.parse(xml_path).getroot()
    rect = root.find('displayRect')
    tags = root.find('tags')
    background = next(t.find('backgroundColor') for t in tags if t.get('type') == 'SetBackgroundColorTag')
    header = {
        'width': int(rect.get('Xmax')) / 20,
        'height': int(rect.get('Ymax')) / 20,
        'fps': float(root.get('frameRate')),
        'frames': int(root.get('frameCount')),
        'background': '#%02x%02x%02x' % tuple(int(background.get(c)) for c in ('red', 'green', 'blue')),
    }
    buttons, placements, display, frame = {}, [], {}, 1
    for tag in tags:
        kind = tag.get('type')
        if kind == 'DefineButtonTag':
            states = {'up': [], 'over': [], 'down': [], 'hit': []}
            for record in tag.find('characters'):
                for state, attr in (('up', 'buttonStateUp'), ('over', 'buttonStateOver'),
                                    ('down', 'buttonStateDown'), ('hit', 'buttonStateHitTest')):
                    if record.get(attr) == 'true':
                        states[state].append((int(record.get('characterId')), matrix(record.find('placeMatrix'))))
            buttons[int(tag.get('buttonId'))] = {'states': states, 'command': fscommand(tag.get('actionBytes'))}
        elif kind == 'RemoveObjectTag':
            placement = display.pop(int(tag.get('depth')), None)
            if placement:
                placement['end'] = frame
        elif kind == 'PlaceObjectTag':
            depth = int(tag.get('depth'))
            placement = {'char': int(tag.get('characterId')), 'depth': depth, 'start': frame,
                         'end': None, 'matrix': matrix(tag.find('matrix'))}
            placements.append(placement)
            display[depth] = placement
        elif kind == 'ShowFrameTag':
            frame += 1
    return header, buttons, placements


def read_shapes(folder, prefix):
    """each shape's SVG in its own coordinates (inside FFDec's outer group, which only moves its bounds to 0,0)"""
    shapes = {}
    for name in os.listdir(folder):
        with open(os.path.join(folder, name), encoding='utf-8') as file:
            svg = file.read()
        body = re.search(r'<svg[^>]*>\s*<g transform="[^"]*">(.*)</g>\s*</svg>', svg, re.S)[1]
        # the photo, embedded by FFDec as a PNG, from the original JPEG instead
        body = re.sub(r'xlink:href="data:image/[^"]+"', f'href="{PHOTO}"', body)
        body = re.sub(r'\s*ffdec:[\w-]+="[^"]*"', '', body)
        body = body.replace('id="PatternID', f'id="{prefix}-pattern').replace('url(#PatternID', f'url(#{prefix}-pattern')
        shapes[int(name.split('.')[0])] = re.sub(r'>\s+<', '><', body.strip())
    return shapes


def uses(records, prefix):
    return ''.join(f'<use href="#{prefix}s{char}"' + (f' transform="{m}"' if m else '') + '/>' for char, m in records)


def build_movie(jar, movie, prefix, photo_out):
    with tempfile.TemporaryDirectory() as tmp:
        ffdec_export(jar, os.path.join(ROOT, movie + '.swf'), tmp)
        header, buttons, placements = read_movie(os.path.join(tmp, 'movie.xml'))
        shapes = read_shapes(os.path.join(tmp, 'shapes'), prefix)
        images = os.listdir(os.path.join(tmp, 'images')) if os.path.isdir(os.path.join(tmp, 'images')) else []
        if images and photo_out:
            shutil.copy(os.path.join(tmp, 'images', images[0]), photo_out)
    defs = ''.join(f'<g id="{prefix}s{char}">{body}</g>' for char, body in sorted(shapes.items()))
    frames, fps = header['frames'], header['fps']
    pct = lambda frame: (frame - 1) / frames * 100
    elements, css = [], []
    # lower depths are drawn first; only placements on screen together share depths
    for i, p in enumerate(sorted(placements, key=lambda p: (p['depth'], p['start']))):
        name = f'{prefix}{i}'
        transform = f' transform="{p["matrix"]}"' if p['matrix'] else ''
        button = buttons.get(p['char'])
        if button:
            states = button['states']
            command = ''
            if button['command']:
                command = f' data-command="{button["command"][0]}" data-args="{button["command"][1]}"'
            inner = ''.join(f'<g class="{state}">{uses(states[state], prefix)}</g>' for state in ('up', 'over', 'down', 'hit'))
            elements.append(f'<g class="{name} button"{transform}{command}>{inner}</g>')
        else:
            elements.append(f'<use class="{name}" href="#{prefix}s{p["char"]}"{transform}/>')
        # shown from its first frame until the frame it is removed (or the end, for the rest of the loop)
        if p['start'] == 1 and p['end'] is None:
            continue
        lines = []
        if p['start'] > 1:
            lines.append('0% { visibility: hidden; }')
        lines.append(f'{pct(p["start"]):.4f}% {{ visibility: visible; }}')
        if p['end'] is not None:
            lines.append(f'{pct(p["end"]):.4f}% {{ visibility: hidden; }}')
        css.append(f'@keyframes {name} {{ ' + ' '.join(lines) + ' }\n'
                   f'.{name} {{ animation-name: {name}; }}')
    return header, defs, elements, css, frames / fps


def page(jar):
    m_header, m_defs, m_elements, m_css, duration = build_movie(jar, 'map', 'm', os.path.join(ROOT, PHOTO))
    c_header, c_defs, c_elements, c_css, _ = build_movie(jar, 'controls', 'c', None)
    mw, mh = m_header['width'], m_header['height']
    cw, ch = c_header['width'], c_header['height']
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Gill Ord - Pig's Tails</title>
<meta name="description" content="Pig's Tails by Gill Ord: a digitally captured video frame, slowly un-picked through time.">
<!--
    Pig's Tails, Gill Ord, produced by e-2. Built by _scripts/build.py from map.swf and controls.swf:
    don't edit by hand. map.swf ({m_header['frames']} frames at {m_header['fps']:g} fps) loops; nothing in it moves,
    each shape and button is shown at exactly the frames it was. The buttons have Flash's states:
    up, over (under the pointer), down (pressed) and hit (the area which takes the pointer).
-->
<style>
html, body {{
    margin: 0;
    height: 100%;
    overflow: hidden;
    background: {m_header['background']};
}}
body {{
    display: flex;
    flex-direction: column;
    height: 100dvh;
}}
/* the frameset's two rows: the map, 90%, and the controls */
#map {{
    flex: 9;
    min-height: 0;
    display: flex;
    align-items: center;
    justify-content: center;
}}
#controls {{
    flex: 1;
    min-height: 0;
    background: {c_header['background']};
}}
#map svg {{
    display: block;
    /* fitted to its frame, as the movie was (SHOWALL) */
    width: min(100vw, 90dvh * {mw:g} / {mh:g});
    height: auto;
    overflow: visible;
}}
/* fitted to the strip's height, at the left (salign l, t) */
#controls svg {{
    display: block;
    height: 100%;
    max-width: 100vw;
}}
#map svg [class] {{
    animation-duration: {duration:.1f}s;
    animation-timing-function: steps(1, end);
    animation-iteration-count: infinite;
}}
/* buttons: only the hit area takes the pointer; it is never seen */
.button > g {{
    pointer-events: none;
}}
.button > .hit {{
    pointer-events: all;
    opacity: 0;
}}
.button > .over,
.button > .down,
.button:hover > .up,
.button:hover:active > .over {{
    display: none;
}}
.button:hover > .over,
.button:hover:active > .down {{
    display: inline;
}}
[data-command] {{
    cursor: pointer;
}}
{chr(10).join(m_css)}
</style>
</head>
<body>
<svg width="0" height="0" style="position: absolute" aria-hidden="true">
    <defs>{m_defs}{c_defs}</defs>
</svg>
<main id="map">
    <svg viewBox="0 0 {mw:g} {mh:g}" role="img" aria-label="Pig's Tails">
        {''.join(m_elements)}
    </svg>
</main>
<nav id="controls">
    <svg viewBox="0 0 {cw:g} {ch:g}" preserveAspectRatio="xMinYMin meet" aria-label="Zoom and pan">
        {''.join(c_elements)}
    </svg>
</nav>
<script>
/*
 * The controls: each button sends an FSCommand, which controls.htm passed to the plugin's
 * scripting methods on the map. Zoom(percent): 50 shows half as much (twice the size), 200 twice
 * as much, 0 all of it. Pan(x, y): moves the view by that many pixels on screen, within the movie.
 */
const svg = document.querySelector('#map svg');
const stage = {{ width: {mw:g}, height: {mh:g} }};
const view = {{ scale: 1, x: stage.width / 2, y: stage.height / 2 }};

function show() {{
    const width = stage.width / view.scale;
    const height = stage.height / view.scale;
    /* the view stays within the movie */
    view.x = Math.min(Math.max(view.x, width / 2), stage.width - width / 2);
    view.y = Math.min(Math.max(view.y, height / 2), stage.height - height / 2);
    svg.setAttribute('viewBox', `${{view.x - width / 2}} ${{view.y - height / 2}} ${{width}} ${{height}}`);
}}

const commands = {{
    zoom(percent) {{
        if (percent === 0) {{
            Object.assign(view, {{ scale: 1, x: stage.width / 2, y: stage.height / 2 }});
        }} else {{
            /* no further out than the whole movie */
            view.scale = Math.max(1, view.scale * 100 / percent);
        }}
    }},
    pan(x, y) {{
        /* screen pixels into the movie's units at the current zoom */
        const units = stage.width / view.scale / svg.getBoundingClientRect().width;
        view.x += x * units;
        view.y += y * units;
    }},
}};
const fscommand = {{
    home: () => commands.zoom(0),
    zoom: args => commands.zoom(parseInt(args)),
    panx: args => commands.pan(parseInt(args), 0),
    pany: args => commands.pan(0, parseInt(args)),
}};

/* Flash buttons act on release over the button: a click */
document.querySelectorAll('[data-command]').forEach(button => button.addEventListener('click', () => {{
    fscommand[button.dataset.command]?.(button.dataset.args);
    show();
}}));
</script>
</body>
</html>
'''


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--ffdec', required=True, help='path to ffdec-cli.jar')
    args = parser.parse_args()
    html = page(args.ffdec)
    with open(os.path.join(ROOT, 'index.html'), 'w', encoding='utf-8') as file:
        file.write(html)
    print(f'index.html: {len(html) // 1024} KB, {PHOTO}')
