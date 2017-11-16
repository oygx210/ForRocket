import numpy as np
import matplotlib.pyplot as plt


class NoshiroAsanai3rd:
    def __init__(self):
        self.launch_point_LLH = [40.138633, 139.984850, 0.0]
        points = []
        points.append([40.139816, 139.983804, 0.0])
        points.append([40.137125, 139.982444, 0.0])
        points.append([40.135588, 139.981298, 0.0])
        points.append([40.134917, 139.981260, 0.0])
        points.append([40.134614, 139.981351, 0.0])
        points.append([40.134459, 139.981516, 0.0])
        points.append([40.134877, 139.982257, 0.0])
        points.append([40.135198, 139.982698, 0.0])
        points.append([40.135512, 139.983439, 0.0])
        points.append([40.136940, 139.984687, 0.0])
        points.append([40.137521, 139.985506, 0.0])
        points.append([40.137521, 139.985506, 0.0])

        self.judge_poly = Judge_inside_poly(self.launch_point_LLH, points)
    
    def in_range(landing_point_ENU):
        x = landing_point_ENU[0]
        y = landing_point_ENU[1]
        judge = self.judge_poly([x, y])
        return judge
        

class NoshiroOchiai3km:
    def __init__(self):
        self.launch_point_LLH = [40.242865, 140.010450, 0.0]
        self.center_point_LLH = [40.248855, 139.975967, 0.0]
        self.radius = 3000.0

        self.judge_circle = Judge_inside_circle(self.launch_point_LLH, self.center_point_LLH, self.radius)
        self.judge_border = Judge_inside_border(self.launch_point_LLH, [40.243015, 140.007566, 0.0], [40.235585, 140.005619, 0.0], [1, -1])
        
    def in_range(landing_point_ENU):
        x = landing_point_ENU[0]
        y = landing_point_ENU[1]
        judge = self.judge_circle([x, y]) and self.judge_border([x, y])
        return judge


class TaikiLand:
    def __init__(self):
        self.launch_point_LLH = [42.514320, 143.439793, 0.0]
        points = []
        points.append([42.514340, 143.439894, 0.0])
        points.append([42.520564, 143.437342, 0.0])
        points.append([42.520939, 143.437916, 0.0])
        points.append([42.521376, 143.438037, 0.0])
        points.append([42.521869, 143.437817, 0.0])
        points.append([42.522543, 143.437870, 0.0])
        points.append([42.522637, 143.440032, 0.0])
        points.append([42.522326, 143.442730, 0.0])
        points.append([42.522068, 143.446304, 0.0])
        points.append([42.519429, 143.449155, 0.0])
        points.append([42.518901, 143.446610, 0.0])
        points.append([42.516320, 143.447509, 0.0])
        points.append([42.516170, 143.446469, 0.0])
        points.append([42.519668, 143.444919, 0.0])
        points.append([42.520032, 143.443932, 0.0])
        points.append([42.519811, 143.443460, 0.0])
        points.append([42.518823, 143.443395, 0.0])
        points.append([42.518657, 143.442861, 0.0])
        points.append([42.517423, 143.443108, 0.0])
        points.append([42.516827, 143.444292, 0.0])
        points.append([42.516107, 143.444170, 0.0])
        points.append([42.515663, 143.445209, 0.0])
        points.append([42.515714, 143.446207, 0.0])
        points.append([42.513618, 143.447081, 0.0])
        points.append([42.513342, 143.445773, 0.0])
        points.append([42.514024, 143.444927, 0.0])
        points.append([42.513465, 143.444155, 0.0])
        points.append([42.513221, 143.440440, 0.0])

        self.judge_poly = Judge_inside_poly(self.launch_point_LLH, points)

    def in_range(landing_point_ENU):
        x = landing_point_ENU[0]
        y = landing_point_ENU[1]
        judge = self.judge_poly([x, y])
        return judge



class Judge_inside_circle:
    def __init__(self, launch_point_LLH, center_point_LLH, radius):
        # LLH : [latitude, longitude, height] = [deg, deg, m]
        coord = Coordinate()
        self.center_point = coord.LLH2ENU(launch_point_LLH, center_point_LLH)
        self.radius = radius

    def __call__(self, landing_point):
        x = landing_point[0]
        y = landing_point[1]
        distance = (x - self.center_point[0]) ** 2 + (y - self.center_point[1])
        judge = True if distance < self.radius**2 else False
        return judge


class Judge_inside_border:
    def __init__(self, launch_point_LLH, edge_point1_LLH, edge_point2_LLH, over_axis=[1,-1]):
        # LLH : [latitude, longitude, height] = [deg, deg, m]
        # over axis: False判定の方向をx,yの単位ベクトルで
        # ENUでE正N負がNG=overなら[1,-1]
        coord = Coordinate()
        self.edge_point1 = coord.LLH2ENU(launch_point_LLH, edge_point1_LLH)
        self.edge_point2 = coord.LLH2ENU(launch_point_LLH, edge_point2_LLH)
        self.over_axis = over_axis

        dx = (self.edge_point2[0] - self.edge_point1[0])
        dy = (self.edge_point2[1] - self.edge_point1[1])
        self.slope = dy / dx if dx != 0 else 0
        self.intercept_y_border = (self.edge_point2[0] * self.edge_point1[1] - self.edge_point1[0] * self.edge_point2[1]) / dx

    def __call__(self, landing_point):
        x = landing_point[0]
        y = landing_point[1]
        move_y = y - self.intercept_y_border
        intercept_y_landing = self.intercept_y_border + move_y - self.slope * x

        judge = True if intercept_y_landing * self.over_axis[1] < self.intercept_y_border * self.over_axis[1] else False
        return judge


class Judge_inside_poly:
    def __init__(self, launch_point_LLH, poly_points_LLH):
        coord = Coordinate()
        poly_points_LLH = poly_points_LLH
        if poly_points_LLH[0] == poly_points_LLH[-1]:
            pass
        else:
            poly_points_LLH.append(poly_points_LLH[0])
        self.poly_points = [coord.LLH2ENU(launch_point_LLH, poly_point_LLH) for poly_point_LLH in poly_points_LLH]


    def __call__(self, landing_point):
        x = landing_point[0]
        y = landing_point[1]
        cross = 0
        for p1, p2 in zip(self.poly_points[:-1], self.poly_points[1:]):
            max_x = max(p1[0], p2[0])
            max_y = max(p1[1], p2[1])
            min_y = min(p1[1], p2[1])

            if y == p1[1]:
                if x < p1[0]:
                    cross += 1
            elif min_y <= y <= max_y and x < max_x:
                dx = p2[0] - p1[0]
                dy = p2[1] - p1[1]
                if dx == 0:
                    if x <= max_x:
                        cross += 1
                elif dy == 0:
                    pass
                else:
                    slope = dy / dx
                    intercept_y = p1[1] - slope * p1[0]
                    x_cross = (y - intercept_y) / slope
                    if x < x_cross:
                        cross += 1
        judge = False if cross % 2 == 0 else True
        return judge


class Coordinate:
    def LLH2ECEF(self, LLH):
        # LLH : [latitude, longitude, height] = [deg, deg, m]
        lat = LLH[0]
        lon = LLH[1]
        height = LLH[2]

        # WGS84 Constant
        a = 6378137.0
        f = 1.0 / 298.257223563
        # e_sq = f * (2.0 - f)
        e_sq = 0.0818191908426 ** 2
        N = a / np.sqrt(1.0 - e_sq * np.power(np.sin(np.radians(lat)), 2))
        point_ECEF = np.zeros(3)
        point_ECEF[0] = (N + height) * np.cos(np.radians(lat)) * np.cos(np.radians(lon))
        point_ECEF[1] = (N + height) * np.cos(np.radians(lat)) * np.sin(np.radians(lon))
        point_ECEF[2] = (N * (1.0 - e_sq) + height) * np.sin(np.radians(lat))
        return point_ECEF

    def LLH2ENU(self, launch_LLH, point_LLH):
        # LLH : [latitude, longitude, height] = [deg, deg, m]
        lat = np.deg2rad(launch_LLH[0])
        lon = np.deg2rad(launch_LLH[1])
        DCM_ECEF2NED = np.array([[-np.sin(lat) * np.cos(lon), -np.sin(lat) * np.sin(lon), np.cos(lat)],
                                [-np.sin(lon)              , np.cos(lon)               , 0.0         ],
                                [-np.cos(lat) * np.cos(lon), -np.cos(lat) * np.sin(lon), -np.sin(lat)]])

        launch_ECEF = self.LLH2ECEF(launch_LLH)
        point_ECEF = self.LLH2ECEF(point_LLH)
        point_ECEF -= launch_ECEF

        point_NED = DCM_ECEF2NED.dot(point_ECEF)
        point_ENU = [point_NED[1], point_NED[0], -point_NED[2]]

        return point_ENU

    def ENU2LLH(self, launch_LLH, point_ENU):
        lat = np.deg2rad(launch_LLH[0])
        lon = np.deg2rad(launch_LLH[1])
        height = launch_LLH[2]
        launch_ECEF = self.LLH2ECEF(launch_LLH)
        e = point_ENU[0]
        n = point_ENU[1]
        u = point_ENU[2]

        x_ecef = -np.sin(lat) * np.cos(lon) * n - np.sin(lon) * e - np.cos(lat) * np.cos(lon) * (-u) + launch_ECEF[0]
        y_ecef = -np.sin(lat) * np.sin(lon) * n + np.cos(lon) * e - np.cos(lat) * np.sin(lon) * (-u) + launch_ECEF[1]
        z_ecef = np.cos(lat) * n - np.sin(lat) * (-u) + launch_ECEF[2]

        # WGS84 Constant
        a = 6378137.0
        f = 1.0 / 298.257223563
        b = a * (1.0 - f)
        e_sq = 2.0 * f - (f * f)
        e2_sq = (e_sq * a * a) / (b * b)

        p = np.sqrt(x_ecef ** 2 + y_ecef ** 2)
        theta = np.arctan2(z_ecef * a, p * b)
        point_LLH = np.zeros(3)
        point_LLH[0] = np.degrees(np.arctan2(z_ecef + e2_sq * b * np.power(np.sin(theta), 3),p - e_sq * a * np.power(np.cos(theta), 3)))
        point_LLH[1] = np.degrees(np.arctan2(y_ecef, x_ecef))
        N = a / np.sqrt(1.0 - e_sq * np.power(np.sin(np.radians(point_LLH[0])), 2))
        point_LLH[2] = (p / np.cos(np.radians(point_LLH[0]))) - N

        return point_LLH


if __name__ == '__main__':
    pass
    # plotter = Plotter()
    # launchsite = NoshiroOchiai3km()
    # launchsite.initialize()
    # point = LandingPointLog('sample.csv')
    # plotter.Plot(launchsite, point)

    

    