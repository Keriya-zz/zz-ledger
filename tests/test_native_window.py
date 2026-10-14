import unittest
from zzledger.native_window import centered_bounds, resize_hit


class NativeGeometryTests(unittest.TestCase):
    def test_edges_corners_and_client_area(self):
        for x, y, expected in [(0,0,13),(999,0,14),(0,799,16),(999,799,17),
                               (0,400,10),(999,400,11),(500,0,12),(500,799,15),
                               (500,400,0),(-1,400,0),(1000,400,0)]:
            with self.subTest(point=(x,y)):
                self.assertEqual(resize_hit(x,y,1000,800), expected)

    def test_work_area_with_taskbar_and_negative_monitor_origin(self):
        self.assertEqual(centered_bounds((0,0,1920,1040),1320,920), (300,60,1320,920))
        self.assertEqual(centered_bounds((-1920,0,0,1040),1320,920), (-1620,60,1320,920))

    def test_high_dpi_window_larger_than_work_area(self):
        self.assertEqual(centered_bounds((0,0,1280,680),1650,1150), (0,0,1280,680))


if __name__ == '__main__': unittest.main()
