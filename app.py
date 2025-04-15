from flask import Flask, render_template, request
import networkx as nx
import heapq
import folium
import numpy as np
import openrouteservice

# OpenRouteService API Key
API_KEY = "5b3ce3597851110001cf62481627160751fe47c7950d9114f79c2d95"  # Replace with your OpenRouteService API key
client = openrouteservice.Client(key=API_KEY)

app = Flask(__name__)

class TrafficNavigationSystem:
    def __init__(self):
        self.graph = nx.Graph()

    def add_road(self, location1, location2, distance):
        self.graph.add_edge(location1, location2, weight=distance)

    def neighbors(self, location):
        return self.graph.neighbors(location)

    def get_cost(self, location1, location2):
        return self.graph[location1][location2]["weight"]

    def heuristic(self, loc1, loc2):
        x1, y1 = loc1
        x2, y2 = loc2
        return np.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2)

    def a_star_search(self, start, goal):
        open_set = []
        heapq.heappush(open_set, (0, start))
        came_from = {}
        g_score = {node: float('inf') for node in self.graph.nodes}
        g_score[start] = 0
        f_score = {node: float('inf') for node in self.graph.nodes}
        f_score[start] = self.heuristic(locations[start], locations[goal])

        while open_set:
            _, current = heapq.heappop(open_set)

            if current == goal:
                path = []
                while current in came_from:
                    path.append(current)
                    current = came_from[current]
                path.append(start)
                return path[::-1]  

            for neighbor in self.neighbors(current):
                tentative_g_score = g_score[current] + self.get_cost(current, neighbor)

                if tentative_g_score < g_score[neighbor]:
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g_score
                    f_score[neighbor] = tentative_g_score + self.heuristic(locations[neighbor], locations[goal])
                    if neighbor not in [i[1] for i in open_set]:
                        heapq.heappush(open_set, (f_score[neighbor], neighbor))

        return None  

    def plot_map(self, path):
        map_ = folium.Map(location=path[0], zoom_start=13)
        for i in range(len(path) - 1):
            folium.Marker(path[i], popup=f"Point {i+1}").add_to(map_)
            folium.PolyLine([path[i], path[i + 1]], color="blue", weight=2.5, opacity=1).add_to(map_)
        folium.Marker(path[-1], popup="Destination", icon=folium.Icon(color="red")).add_to(map_)
        return map_

    def get_real_distance(self, start_coords, end_coords):
        """Fetch real-world distance using OpenRouteService API."""
        try:
            route = client.directions(
                coordinates=[start_coords[::-1], end_coords[::-1]],  
                profile="driving-car",
                format="geojson",
            )
            distance = route["features"][0]["properties"]["segments"][0]["distance"] / 1000  # Convert meters to km
            return distance
        except Exception as e:
            print("Error fetching real-world distance:", e)
            return None  
    

# Initialize the Traffic Navigation System
traffic_system = TrafficNavigationSystem()

# Add locations and roads
locations = {}

@app.route('/')
def index():
    return render_template('index.html')
@app.route('/find_route', methods=['POST'])
def find_route():
    start_city = request.form['start']
    end_city = request.form['destination']

    start_coords = get_coordinates(start_city)
    end_coords = get_coordinates(end_city)

    if start_coords and end_coords:
        if start_city not in locations:
            locations[start_city] = start_coords
        if end_city not in locations:
            locations[end_city] = end_coords

        distance = traffic_system.get_real_distance(start_coords, end_coords)
        if distance is not None:
            traffic_system.add_road(start_city, end_city, distance)

            a_star_path = traffic_system.a_star_search(start_city, end_city)
            if a_star_path:
                map_ = traffic_system.plot_map([locations[loc] for loc in a_star_path])
                map_.save("static/route_map.html")
                return render_template('result.html', path=a_star_path, distance=distance)
            else:
                return render_template('result.html', path=None, distance=None)
        else:
            return render_template('result.html', path=None, distance=None)
    else:
        return render_template('result.html', path=None, distance=None)

def get_coordinates(city_name):
    """Fetch the latitude and longitude of a given city using OpenRouteService Geocoding API."""
    try:
        result = client.pelias_search(city_name)
        if result and "features" in result and len(result["features"]) > 0:
            coords = result["features"][0]["geometry"]["coordinates"]
            return coords[1], coords[0]  # Return as (latitude, longitude)
        else:
            print(f"Could not find coordinates for '{city_name}'.")
            return None
    except Exception as e:
        print(f"Error fetching coordinates: {e}")
        return None

if __name__ == "__main__":
    app.run(debug=True) 