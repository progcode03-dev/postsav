from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
ROOT=Path(__file__).resolve().parents[1]/'static'
GREEN,PAPER,INK,PALE='#235d45','#f5f3ed','#202e29','#e2e8dc'
def font(size,serif=False):
 paths=[Path('C:/Windows/Fonts/georgia.ttf' if serif else 'C:/Windows/Fonts/segoeui.ttf'),Path('/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf' if serif else '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')]
 return next((ImageFont.truetype(str(p),size) for p in paths if p.exists()),ImageFont.load_default(size=size))
def mark():
 im=Image.new('RGBA',(1024,1024)); d=ImageDraw.Draw(im); u=16
 d.rounded_rectangle((0,0,1023,1023),radius=192,fill=GREEN)
 d.polygon([(x*u,y*u) for x,y in [(18,12),(38,12),(48,22),(48,44),(32,52),(18,44)]],fill=PAPER)
 d.polygon([(x*u,y*u) for x,y in [(38,12),(38,22),(48,22)]],fill='#a4b79b')
 d.rounded_rectangle((25*u,25*u,40*u,37*u),radius=5*u,fill=GREEN);d.rectangle((25*u,25*u,29*u,43*u),fill=GREEN)
 d.rounded_rectangle((29*u,29*u,36*u,33*u),radius=2*u,fill=PAPER)
 return im
def build():
 im=mark(); (ROOT/'icons').mkdir(exist_ok=True)
 for size in (48,96,192,512): im.resize((size,size),Image.Resampling.LANCZOS).save(ROOT/f'icons/icon-{size}.png',optimize=True)
 im.resize((180,180),Image.Resampling.LANCZOS).save(ROOT/'icons/apple-touch-icon.png')
 im.resize((256,256),Image.Resampling.LANCZOS).save(ROOT/'icons/favicon.ico',sizes=[(16,16),(32,32),(48,48)])
 (ROOT/'favicon.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="12" fill="#235d45"/><path d="M18 12h20l10 10v22l-16 8-14-8z" fill="#f5f3ed"/><path d="M38 12v10h10" fill="#a4b79b"/><path d="M25 43V25h10a6 6 0 0 1 0 12h-6v6zm4-14v4h6a2 2 0 0 0 0-4z" fill="#235d45"/></svg>\n',encoding='utf-8')
 card=Image.new('RGB',(1200,630),PAPER); d=ImageDraw.Draw(card); logo=im.resize((76,76),Image.Resampling.LANCZOS);card.paste(logo,(64,50),logo)
 d.text((156,61),'PostSav',font=font(40),fill=INK);d.line((64,156,1136,156),fill='#c6cfbf',width=2)
 d.text((64,198),'A post. A proper file.',font=font(66,True),fill=INK)
 d.text((66,310),'Save public images, videos & carousel slides.',font=font(28),fill=GREEN)
 d.text((66,362),'Instagram  /  LinkedIn  /  Pinterest',font=font(25),fill=INK)
 for i,label in enumerate(['MP4','JPG','ZIP']):
  x=66+i*185;d.rectangle((x,460,x+160,536),fill=PALE,outline='#c6cfbf',width=2);d.text((x+44,480),label,font=font(26),fill=GREEN)
 d.text((800,500),'Free. No account needed.',font=font(22),fill=INK);card.save(ROOT/'img/og-image.jpg',quality=90,optimize=True)
 for name,size,label,caption in [('images',(720,1080),'JPG','ONE FRAME'),('video',(720,484),'MP4','MOVING PICTURES'),('slides',(720,480),'SLIDES','IN SEQUENCE'),('zip',(720,480),'ZIP','ALL TOGETHER')]:
  canvas=Image.new('RGB',size,PALE if name!='video' else '#e9e1d4');d=ImageDraw.Draw(canvas);y=(size[1]-270)//2
  for i in range(3 if name=='slides' else 1):
   x=236+i*52;d.polygon([(x,y+i*12),(x+148,y+i*12),(x+204,y+56+i*12),(x+204,y+270+i*12),(x,y+270+i*12)],fill=PAPER,outline=GREEN,width=3)
   d.line([(x+148,y+i*12),(x+148,y+56+i*12),(x+204,y+56+i*12)],fill=GREEN,width=2)
   d.text((x+24,y+118+i*12),label if name!='slides' else f'0{i+1}',font=font(35,True),fill=GREEN)
  d.text((34,28),caption,font=font(18),fill=GREEN);canvas.save(ROOT/f'img/feature-{name}.webp',quality=85,method=6)
 print('Brand assets rebuilt.')
if __name__=='__main__': build()
