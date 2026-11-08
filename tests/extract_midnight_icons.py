"""Reproduce native-resolution extractions from the approved RGB reference.

Only background unmatting is performed. No generation, redraw or upscaling.
Run from the repository root. The source sheet and Light assets are read-only.
"""
import json
from pathlib import Path
from statistics import median
from PIL import Image, ImageOps

SOURCE=Path('design-reference/icons-midnight.png')
OUTPUT=Path('assets/midnight-icons')
# Names/order were checked against the labels on the approved 1536x1024 sheet.
# Rectangles exclude captions and tile frames; dimensions remain native pixels.
ITEMS=[
    ('Sunny','sunny',(235,104,375,220)),
    ('Clear','clear',(465,104,640,220)),
    ('Cloudy','cloudy',(722,112,900,217)),
    ('Sunshower','sunshower',(240,299,400,420)),
    ('Light Rain','light-rain',(506,299,655,420)),
    ('Moderate Rain','moderate-rain',(772,299,929,420)),
    ('Heavy Rain','heavy-rain',(1040,299,1200,420)),
    ('Moon Rain','moon-rain',(1311,299,1475,420)),
    ('Light Snow','light-snow',(242,493,406,603)),
    ('Snow','snow',(510,493,674,603)),
    ('Heavy Snow','heavy-snow',(778,493,948,603)),
    ('Rainbow','rainbow',(230,684,416,780)),
    ('Moon Rainbow','moon-rainbow',(500,682,686,780)),
    ('Meteor Shower 1','meteor-shower-1',(790,682,950,780)),
    ('Meteor Shower 2','meteor-shower-2',(1049,682,1220,780)),
    ('Meteor Shower 3','meteor-shower-3',(1305,682,1482,780)),
    ('Aurora 1','aurora-1',(240,835,407,950)),
    ('Aurora 2','aurora-2',(510,835,678,950)),
    ('Aurora 3','aurora-3',(775,835,947,950)),
    ('Heatwave','heatwave',(1048,835,1210,950)),
    ('Petal Rain','petal-rain',(1315,835,1477,950)),
]

def extract(source,box):
    crop=source.crop(box).convert('RGB')
    width,height=crop.size
    output=Image.new('RGBA',crop.size)
    pixels=crop.load()
    for y in range(height):
        # Dark catalog paper varies gently along each row. Estimate it from
        # the two blank margins, then unmatte the original neon RGB samples.
        left=[median(pixels[x,y][c] for x in range(3)) for c in range(3)]
        right=[median(pixels[width-1-x,y][c] for x in range(3)) for c in range(3)]
        for x in range(width):
            background=[left[c]+(right[c]-left[c])*x/(width-1) for c in range(3)]
            rgb=pixels[x,y]
            signal=max(rgb[c]-background[c] for c in range(3))
            alpha=max(0,min(1,(signal-4)/48))
            if alpha:
                color=tuple(round(max(0,min(255,(rgb[c]-(1-alpha)*background[c])/alpha))) for c in range(3))
                output.putpixel((x,y),color+(round(alpha*255),))
    # Discard isolated paper/frame remnants with no bright neon core. Keep all
    # connected soft glow surrounding the original bright outline.
    visited=set()
    for y in range(height):
        for x in range(width):
            if (x,y) in visited or output.getpixel((x,y))[3]<=5:
                continue
            todo=[(x,y)];visited.add((x,y));component=[];core=False
            while todo:
                px,py=todo.pop();component.append((px,py));r,g,b,a=output.getpixel((px,py))
                core=core or (a>=180 and max(r,g,b)>=180)
                for dy in [-1,0,1]:
                    for dx in [-1,0,1]:
                        point=(px+dx,py+dy)
                        if 0<=point[0]<width and 0<=point[1]<height and point not in visited and output.getpixel(point)[3]>5:
                            visited.add(point);todo.append(point)
            if not core:
                for point in component:output.putpixel(point,(0,0,0,0))
    return ImageOps.expand(output,border=6,fill=(0,0,0,0))

def main():
    source=Image.open(SOURCE)
    if source.size!=(1536,1024):
        raise ValueError('Reference dimensions changed; recheck all crop rectangles.')
    OUTPUT.mkdir(exist_ok=True)
    manifest={}
    contact=Image.new('RGB',(7*210,3*150),'#1c2340')
    for index,(weather,slug,box) in enumerate(ITEMS):
        icon=extract(source,box)
        icon.save(OUTPUT/(slug+'.png'))
        manifest[weather]={'file':slug+'.png','size':list(icon.size),'sourceBox':list(box),'transparentPadding':6}
        # Native-size QA contact sheet; not a website asset or upscaled preview.
        x=(index%7)*210+(210-icon.width)//2
        y=(index//7)*150+(150-icon.height)//2
        contact.paste(icon,(x,y),icon)
    (OUTPUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    import tempfile
    path=Path(tempfile.gettempdir())/'heartopia-midnight-extractions.png'
    contact.save(path)
    print('Extracted',len(manifest),'native-resolution RGBA icons. QA:',path)

if __name__=='__main__':
    main()
