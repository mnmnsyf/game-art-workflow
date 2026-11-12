"""Local regression tests for production helpers; no network or generation."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import os
import struct

from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent


class MatteTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def run_tool(self, *args):
        return subprocess.run([sys.executable, '-B', str(HERE / 'matte_image.py'), *map(str, args)],
                              capture_output=True, text=True, encoding='utf8')

    def test_existing_alpha_keeps_pixels_and_source(self):
        src = self.root / 'native.png'
        im = Image.new('RGBA', (16, 16), (90, 40, 20, 0))
        im.putpixel((8, 8), (130, 80, 30, 128))
        im.save(src)
        before = src.read_bytes()
        out = self.root / 'result.png'
        result = self.run_tool(src, '--out', out)
        self.assertEqual(result.returncode, 0, result.stderr)
        with Image.open(out) as actual:
            self.assertEqual(actual.tobytes(), im.tobytes())
        self.assertEqual(before, src.read_bytes())

    def test_connected_background_keeps_enclosed_same_color(self):
        src = self.root / 'solid.png'
        im = Image.new('RGB', (24, 24), 'white')
        ImageDraw.Draw(im).rectangle((6, 6, 17, 17), outline='black', width=2)
        im.save(src)
        out = self.root / 'result.png'
        result = self.run_tool(src, '--out', out)
        self.assertEqual(result.returncode, 0, result.stderr)
        with Image.open(out) as actual:
            self.assertEqual(actual.getpixel((0, 0))[3], 0)
            self.assertEqual(actual.getpixel((12, 12))[3], 255)

    def test_mask_unmix_recovers_soft_edge(self):
        src = self.root / 'composite.png'
        Image.new('RGB', (8, 8), (227, 167, 137)).save(src)
        mask = self.root / 'mask.png'
        Image.new('L', (8, 8), 128).save(mask)
        out = self.root / 'result.png'
        result = self.run_tool(src, '--out', out, '--mask', mask, '--bg', '#ffffff', '--unmix')
        self.assertEqual(result.returncode, 0, result.stderr)
        with Image.open(out) as actual:
            px = actual.getpixel((0, 0))
            self.assertEqual(px[3], 128)
            self.assertTrue(all(abs(a-b) <= 2 for a, b in zip(px[:3], (200, 80, 20))))
        report = json.loads(result.stdout)
        self.assertTrue(Path(report['preview']).exists())

    def test_ambiguous_background_refuses_before_writing(self):
        src = self.root / 'ambiguous.png'
        im = Image.new('RGB', (16, 16), 'white')
        im.putpixel((0, 0), (0, 0, 0));im.save(src)
        out = self.root / 'result.png'
        result = self.run_tool(src, '--out', out)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(out.exists())

    def test_source_overwrite_is_rejected(self):
        src = self.root / 'source.png'
        Image.new('RGB', (8, 8), 'white').save(src)
        before = hashlib.sha256(src.read_bytes()).hexdigest()
        result = self.run_tool(src, '--out', src)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(hashlib.sha256(src.read_bytes()).hexdigest(), before)


@unittest.skipUnless(os.environ.get('ART_TEST_BLENDER'), 'set ART_TEST_BLENDER for actual Blender rendering')
class RenderTests(unittest.TestCase):
    def test_twelve_diagnostic_views_without_source_mutation(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / 'cube.glb'
            vertices = [(-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),(-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1)]
            indices = [0,2,1,0,3,2,4,5,6,4,6,7,0,1,5,0,5,4,3,7,6,3,6,2,0,4,7,0,7,3,1,2,6,1,6,5]
            binary = b''.join(struct.pack('<3f', *v) for v in vertices)+struct.pack('<36H', *indices)
            document = {'asset':{'version':'2.0'},'buffers':[{'byteLength':len(binary)}],
                        'bufferViews':[{'buffer':0,'byteOffset':0,'byteLength':96},{'buffer':0,'byteOffset':96,'byteLength':72}],
                        'accessors':[{'bufferView':0,'componentType':5126,'count':8,'type':'VEC3','min':[-1,-1,-1],'max':[1,1,1]},
                                     {'bufferView':1,'componentType':5123,'count':36,'type':'SCALAR'}],
                        'meshes':[{'primitives':[{'attributes':{'POSITION':0},'indices':1}]}],
                        'nodes':[{'mesh':0}],'scenes':[{'nodes':[0]}],'scene':0}
            body = json.dumps(document).encode();body += b' '*(-len(body)%4)
            source.write_bytes(struct.pack('<4sII',b'glTF',2,28+len(body)+len(binary))+
                               struct.pack('<I4s',len(body),b'JSON')+body+struct.pack('<I4s',len(binary),b'BIN\0')+binary)
            before = source.read_bytes()
            output = root / 'review'
            result = subprocess.run([os.environ['ART_TEST_BLENDER'], '--background', '--python-exit-code', '1',
                                     '--python', str(HERE/'render_asset.py'), '--', str(source), '--out', str(output),
                                     '--resolution','64','--samples','1'], capture_output=True, text=True, encoding='utf8')
            self.assertEqual(result.returncode,0,result.stdout[-2500:]+result.stderr[-2500:])
            report = json.loads((output/'stats.json').read_text())
            self.assertEqual(report['triangles'],12)
            self.assertEqual(report['boundary_edges_after_statistical_weld'],0)
            self.assertEqual(len(report['views']),12)
            self.assertEqual(report['source_sha256'],hashlib.sha256(before).hexdigest())
            self.assertTrue(all((output/v).is_file() for v in report['views']))
            self.assertEqual(source.read_bytes(),before)


if __name__ == '__main__':
    unittest.main()
