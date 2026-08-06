import pyglet


class FixationTarget:
    def __init__(
        self,
        x: float,
        y: float,
        ring_radius: float = 8,
        center_radius: float = 2,
        ring_color: tuple[int, int, int] = (0, 0, 0),
        center_color: tuple[int, int, int] = (255, 255, 255),
    ):
        self.batch = pyglet.graphics.Batch()
        self.ring = pyglet.shapes.Circle(
            x, y, ring_radius, color=ring_color, batch=self.batch
        )
        self.center = pyglet.shapes.Circle(
            x, y, center_radius, color=center_color, batch=self.batch
        )

    def move(self, x: float, y: float):
        self.ring.x = x
        self.ring.y = y
        self.center.x = x
        self.center.y = y

    def draw(self):
        self.batch.draw()
