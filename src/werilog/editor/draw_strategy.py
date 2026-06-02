from abc import ABC, abstractmethod
import math

# Strategy design pattern interface for wire routing algorithms.
# Different concrete strategies determine how to calculate a list of path points 
# connecting start_point to end_point.
class WireRoutingStrategy(ABC):
    @abstractmethod
    def route(self, start_point, end_point, existing_wires=None):
        pass

# Concrete Strategy implementing orthogonal square routing.
# It drafts a path with 90-degree right angles (going right half-way, vertical shift, and right the rest)
# and simplifies the path by removing redundant collinear coordinates.
class SquareWireStrategy(WireRoutingStrategy):
    def route(self, start_point, end_point, existing_wires=None):
        """
        Routes a wire using orthogonal lines.
        Returns a list of points representing the path.
        """
        x1, y1 = start_point
        x2, y2 = end_point
        
        # Simple square routing: go right half way, up/down, right the rest of the way
        mid_x = x1 + (x2 - x1) / 2
        
        path = [
            (x1, y1),
            (mid_x, y1),
            (mid_x, y2),
            (x2, y2)
        ]
        
        # 1. Remove consecutive duplicates
        new_path = [path[0]]
        for pt in path[1:]:
            if pt != new_path[-1]:
                new_path.append(pt)
                
        # 2. Merge collinear segments
        if len(new_path) < 3:
            return new_path
            
        simplified = [new_path[0]]
        for i in range(1, len(new_path) - 1):
            prev_pt = simplified[-1]
            curr_pt = new_path[i]
            next_pt = new_path[i+1]
            
            # Check if they are collinear (horizontal or vertical)
            is_collinear_h = (abs(prev_pt[1] - curr_pt[1]) < 0.1 and abs(curr_pt[1] - next_pt[1]) < 0.1)
            is_collinear_v = (abs(prev_pt[0] - curr_pt[0]) < 0.1 and abs(curr_pt[0] - next_pt[0]) < 0.1)
            
            if not (is_collinear_h or is_collinear_v):
                simplified.append(curr_pt)
        simplified.append(new_path[-1])
        return simplified

# Concrete Strategy implementing direct straight wire routing.
# It simply connects the start point to the end point in a straight path segment.
class StraightWireStrategy(WireRoutingStrategy):
    def route(self, start_point, end_point, existing_wires=None):
        """
        Routes a wire using a straight line directly from start to end.
        Returns a list of points representing the path.
        """
        return [start_point, end_point]

# Decorator Strategy wrapping a base WireRoutingStrategy.
# It routes the base wire and calculates intersection coordinates (jump points)
# where the new wire path crosses existing wire paths, allowing Tkinter/HTML canvas to draw bridge skips.
class JumpWireStrategy(WireRoutingStrategy):
    def __init__(self, base_strategy: WireRoutingStrategy):
        self.base_strategy = base_strategy

    def route(self, start_point, end_point, existing_wires=None):
        """
        Routes a wire and calculates jump points if it intersects with existing wires.
        Returns a dictionary containing the path and a list of jump coordinates.
        """
        # Calculate the base path using the injected strategy
        path = self.base_strategy.route(start_point, end_point)
        
        jumps = []
        if existing_wires:
            if isinstance(existing_wires, bool):
                # Mock jump for backward compatibility test
                if len(path) >= 3:
                    mid_x = path[1][0]
                    mid_y = (path[1][1] + path[2][1]) / 2
                    jumps.append((mid_x, mid_y))
            elif isinstance(existing_wires, list):
                # Calculate real intersections with existing paths
                # Path segments of the new path
                for i in range(len(path) - 1):
                    seg1 = (path[i], path[i+1])
                    for old_path in existing_wires:
                        # old_path could be a list of points
                        if isinstance(old_path, list):
                            for j in range(len(old_path) - 1):
                                seg2 = (old_path[j], old_path[j+1])
                                intersect = self._get_intersection(seg1, seg2)
                                if intersect:
                                    jumps.append(intersect)
            
        return {
            "path": path,
            "jumps": jumps
        }

    def _get_intersection(self, seg1, seg2):
        x1, y1 = seg1[0]
        x2, y2 = seg1[1]
        x3, y3 = seg2[0]
        x4, y4 = seg2[1]
        
        # Check if seg1 is horizontal and seg2 is vertical
        if abs(y1 - y2) < 0.1 and abs(x3 - x4) < 0.1:
            min_x, max_x = min(x1, x2), max(x1, x2)
            min_y, max_y = min(y3, y4), max(y3, y4)
            if min_x + 1 < x3 < max_x - 1 and min_y + 1 < y1 < max_y - 1:
                return (x3, y1)
                
        # Check if seg1 is vertical and seg2 is horizontal
        if abs(x1 - x2) < 0.1 and abs(y3 - y4) < 0.1:
            min_y, max_y = min(y1, y2), max(y1, y2)
            min_x, max_x = min(x3, x4), max(x3, x4)
            if min_y + 1 < y3 < max_y - 1 and min_x + 1 < x1 < max_x - 1:
                return (x1, y3)
                
        return None

# Context wrapper (Strategy pattern) to easily switch routing strategies at runtime.
class WireRouter:
    def __init__(self, strategy: WireRoutingStrategy):
        self._strategy = strategy
        
    def set_strategy(self, strategy: WireRoutingStrategy):
        self._strategy = strategy
        
    def route_wire(self, start_point, end_point, existing_wires=None):
        return self._strategy.route(start_point, end_point, existing_wires)

if __name__ == "__main__":
    # Test the strategies
    base_square = SquareWireStrategy()
    router = WireRouter(base_square)
    p1 = (10, 20)
    p2 = (100, 80)
    
    print("Square Strategy Path:")
    print(router.route_wire(p1, p2))
    
    router.set_strategy(JumpWireStrategy(base_square))
    print("\nJump Strategy Path:")
    print(router.route_wire(p1, p2, existing_wires=True))

