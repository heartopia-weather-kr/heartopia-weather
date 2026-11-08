import json
from pathlib import Path
import unittest
from PIL import Image

class MidnightAssetsTest(unittest.TestCase):
    def test_all_native_transparent_images(self):
        manifest=json.loads(Path('assets/midnight-icons/manifest.json').read_text())
        self.assertEqual(len(manifest),21)
        for key,item in manifest.items():
            with self.subTest(weather=key):
                image=Image.open(Path('assets/midnight-icons')/item['file'])
                self.assertEqual(image.mode,'RGBA')
                self.assertEqual(list(image.size),item['size'])
                x0,y0,x1,y1=item['sourceBox'];pad=item['transparentPadding']
                self.assertEqual(image.size,(x1-x0+2*pad,y1-y0+2*pad))
                alpha=image.getchannel('A')
                self.assertEqual(alpha.getextrema(),(0,255))
                box=alpha.getbbox()
                self.assertGreaterEqual(box[0],pad)
                self.assertGreaterEqual(box[1],pad)
                self.assertLessEqual(box[2],image.width-pad)
                self.assertLessEqual(box[3],image.height-pad)

if __name__=='__main__':
    unittest.main()
