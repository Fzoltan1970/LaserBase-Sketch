# vectorizer.py
import cv2
import numpy as np

class Vectorizer:
    def __init__(self, min_length=15, epsilon=1.5):
        self.min_length = min_length
        self.epsilon = epsilon

    # ---------------------------------------------------------
    # PUBLIC
    # ---------------------------------------------------------
    def vectorize(self, line_map, detail=None, smooth=None, merge=None):

        if len(line_map.shape) == 3:
            gray = cv2.cvtColor(line_map, cv2.COLOR_BGR2GRAY)
        else:
            gray = line_map.copy()

        bw = (gray < 200).astype(np.uint8)

        # --- slider értékek alkalmazása ---
        if detail is not None:
            self.min_length = 2 + (100 - detail) * 0.25   # rövid vonalak szűrése

        if smooth is not None:
            self.epsilon = 0.5 + smooth * 0.04            # görbe simítása

        print("ink pixels:", np.count_nonzero(bw))
        print("image size:", bw.shape)

        visited = np.zeros_like(bw, dtype=np.uint8)
        h, w = bw.shape
        paths = []

        # 8 szomszéd
        N = [(-1,-1),(-1,0),(-1,1),
             ( 0,-1),       (0,1),
             ( 1,-1),(1,0),(1,1)]

        def trace(x, y):
            path = [(x,y)]
            visited[y,x] = 1

            cx, cy = x, y
            while True:
                found = False
                for dx,dy in N:
                    nx, ny = cx+dx, cy+dy
                    if 0<=nx<w and 0<=ny<h:
                        if bw[ny,nx] and not visited[ny,nx]:
                            visited[ny,nx] = 1
                            path.append((nx,ny))
                            cx,cy = nx,ny
                            found = True
                            break
                if not found:
                    break
            return path

        for y in range(h):
            for x in range(w):
                if bw[y,x] and not visited[y,x]:
                    p = trace(x,y)
                    if len(p) > self.min_length:
                        paths.append(self._simplify(p))

        print("paths:", len(paths))
        return paths

    def _merge_paths(self, paths, dist=2.5, angle=35):

        import math

        def ang(a,b):
            dx=b[0]-a[0]
            dy=b[1]-a[1]
            return math.degrees(math.atan2(dy,dx))

        merged = True
        while merged:
            merged=False

            for i in range(len(paths)):
                if merged: break
                for j in range(i+1,len(paths)):
                    p1=paths[i]
                    p2=paths[j]

                    a1=p1[-2]; a2=p1[-1]
                    b1=p2[0];  b2=p2[1]

                    d=((a2[0]-b1[0])**2+(a2[1]-b1[1])**2)**0.5
                    if d>dist: continue

                    da=ang(a1,a2)
                    db=ang(b1,b2)

                    if abs(da-db)<angle:
                        paths[i]=p1+p2
                        del paths[j]
                        merged=True
                        break

        return paths

    # ---------------------------------------------------------
    # TRACE CONTOURS
    # ---------------------------------------------------------
    def _trace_strokes(self, edge):
        img = (edge * 255).astype(np.uint8)
        contours, _ = cv2.findContours(img, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)

        paths = []
        for c in contours:
            pts = [(int(p[0][0]), int(p[0][1])) for p in c]
            if len(pts) > 1:
                paths.append(pts)
        return paths

    # ---------------------------------------------------------
    # SIMPLIFY POLYLINE
    # ---------------------------------------------------------
    def _simplify(self, path):
        cnt = np.array(path, dtype=np.int32).reshape((-1,1,2))
        approx = cv2.approxPolyDP(cnt, self.epsilon, False)
        return [(int(p[0][0]), int(p[0][1])) for p in approx]

    # ---------------------------------------------------------
    # PREVIEW
    # ---------------------------------------------------------
    def draw_preview(self, shape, paths):
        h, w = shape[:2]
        canvas = np.ones((h, w, 3), dtype=np.uint8) * 255

        for path in paths:
            for i in range(len(path)-1):
                cv2.line(canvas, path[i], path[i+1], (0,0,0), 1, cv2.LINE_AA)

        return canvas
