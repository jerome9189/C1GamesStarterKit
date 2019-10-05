import gamelib
import random
import math
import warnings
from sys import maxsize
import json


"""
Most of the algo code you write will be in this file unless you create new
modules yourself. Start by modifying the 'on_turn' function.

Advanced strategy tips: 

  - You can analyze action frames by modifying on_action_frame function

  - The GameState.map object can be manually manipulated to create hypothetical 
  board states. Though, we recommended making a copy of the map to preserve 
  the actual current map state.
"""

class AlgoStrategy(gamelib.AlgoCore):
    def __init__(self):
        super().__init__()
        seed = random.randrange(maxsize)
        random.seed(seed)
        self.min_ping_threshold = 6
        self.ping_cannon_last_turn = False
        self.last_enemy_health = 40
        gamelib.debug_write('Random seed: {}'.format(seed))

    def on_game_start(self, config):
        """ 
        Read in config and perform any initial setup here 
        """
        gamelib.debug_write('Configuring your custom algo strategy...')
        self.config = config
        global FILTER, ENCRYPTOR, DESTRUCTOR, PING, EMP, SCRAMBLER
        FILTER = config["unitInformation"][0]["shorthand"]
        ENCRYPTOR = config["unitInformation"][1]["shorthand"]
        DESTRUCTOR = config["unitInformation"][2]["shorthand"]
        PING = config["unitInformation"][3]["shorthand"]
        EMP = config["unitInformation"][4]["shorthand"]
        SCRAMBLER = config["unitInformation"][5]["shorthand"]
        # This is a good place to do initial setup
        self.scored_on_locations = []

    
    def on_turn(self, turn_state):
        """
        This function is called every turn with the game state wrapper as
        an argument. The wrapper stores the state of the arena and has methods
        for querying its state, allocating your current resources as planned
        unit deployments, and transmitting your intended deployments to the
        game engine.
        """
        game_state = gamelib.GameState(self.config, turn_state)
        gamelib.debug_write('Performing turn {} of your custom algo strategy'.format(game_state.turn_number))
        game_state.suppress_warnings(True)  #Comment or remove this line to enable warnings.

        self.starter_strategy(game_state)

        game_state.submit_turn()


    """
    NOTE: All the methods after this point are part of the sample starter-algo
    strategy and can safely be replaced for your custom algo.
    """

    def starter_strategy(self, game_state):
        """
        For defense we will use a spread out layout and some Scramblers early on.
        We will place destructors near locations the opponent managed to score on.
        For offense we will use long range EMPs if they place stationary units near the enemy's front.
        If there are no stationary units to attack in the front, we will send Pings to try and score quickly.
        """
        # First, place basic defenses
        self.build_defences(game_state)
        # Now build reactive defenses based on where the enemy scored
        self.build_reactive_defense(game_state)
        
        if game_state._player_resources[1]['bits'] >= self.min_ping_threshold and game_state.my_health < game_state.enemy_health: 
            self.stall_with_scramblers(game_state)

        if self.ping_cannon_last_turn and (self.last_enemy_health == game_state.enemy_health):
            self.min_ping_threshold = int(self.min_ping_threshold * 1.5)

        if game_state._player_resources[0]['bits'] >= self.min_ping_threshold:           
            self.ping_cannon(game_state, game_state._player_resources[0]['bits'])
            self.ping_cannon_last_turn = True
        else:
            self.ping_cannon_last_turn = False
        
        if game_state._player_resources[1]['bits'] >= self.min_ping_threshold and game_state.my_health >= game_state.enemy_health: 
            self.stall_with_scramblers(game_state)
        

        # If the turn is less than 5, stall with Scramblers and wait to see enemy's base
        # if game_state.turn_number < 5:
        #     self.stall_with_scramblers(game_state)
        # else:
        #     # Now let's analyze the enemy base to see where their defenses are concentrated.
        #     # If they have many units in the front we can build a line for our EMPs to attack them at long range.
        #     if self.detect_enemy_unit(game_state, unit_type=None, valid_x=None, valid_y=[14, 15]) > 10:
        #         self.emp_line_strategy(game_state)
        #     else:
        #         # They don't have many units in the front so lets figure out their least defended area and send Pings there.

        #         # Only spawn Ping's every other turn
        #         # Sending more at once is better since attacks can only hit a single ping at a time
        #         if game_state.turn_number % 2 == 1:
        #             # To simplify we will just check sending them from back left and right
        #             ping_spawn_location_options = [[13, 0], [14, 0]]
        #             best_location = self.least_damage_spawn_location(game_state, ping_spawn_location_options)
        #             game_state.attempt_spawn(PING, best_location, 1000)

        #         # Lastly, if we have spare cores, let's build some Encryptors to boost our Pings' health.
        #         encryptor_locations = [[13, 2], [14, 2], [13, 3], [14, 3]]
        #         game_state.attempt_spawn(ENCRYPTOR, encryptor_locations)

    def ping_cannon(self, game_state, pings):
        ping_cannon_spawn = self.least_damage_spawn_location(game_state, self.get_nice_spawn(game_state))
        for i in range(int(pings)):
            game_state.attempt_spawn(PING, ping_cannon_spawn)

    def build_defences(self, game_state):
        """
        Build basic defenses using hardcoded locations.
        Remember to defend corners and avoid placing units in the front where enemy EMPs can attack them.
        """
        # Useful tool for setting up your base locations: https://www.kevinbai.design/terminal-map-maker
        # More community tools available at: https://terminal.c1games.com/rules#Download

        destructors_points = [[0, 13], [1, 13], [2, 13], [25, 13], [26, 13], [27, 13], [5, 10], [22, 10], [8, 7], [19, 7], [11, 4], [16, 4], [12, 3], [15, 3]]
        encryptors_points = [[3, 12], [24, 12], [4, 11], [23, 11], [6, 9], [21, 9], [7, 8], [20, 8], [9, 6], [18, 6], [10, 5], [17, 5]]

        # Encrypter locations
        game_state.attempt_spawn(ENCRYPTOR, encryptors_points)

        # attempt_spawn will try to spawn units if we have resources, and will check if a blocking unit is already there
        game_state.attempt_spawn(DESTRUCTOR, destructors_points)

    def build_triangle_funnel(self, game_state, side='right'):
        if side.startswith('r'):
            spawn_points = [[15, 13], [16, 13], [17, 13], [18, 13], [19, 13], [20, 13], [21, 13], [22, 13], [21, 12], [14, 11], [20, 11], [14, 10], [19, 10], [18, 9], [14, 8], [17, 8], [14, 7], [16, 7], [15, 6]]
            destructor_points = [[14, 13], [14, 12], [14, 9], [14, 6], [14, 5]]
        elif side.startswith('l'):
            spawn_points = [[5, 13], [6, 13], [7, 13], [8, 13], [9, 13], [10, 13], [11, 13], [6, 12], [7, 11], [12, 11], [8, 10], [9, 9], [12, 9], [10, 8], [12, 8], [11, 7], [12, 6]]
            destructor_points = [[12, 13], [12, 12], [12, 10], [12, 7]]
        else:
            spawn_points = []
            destructor_points = []
    
        for _ in spawn_points:
            game_state.attempt_spawn(ENCRYPTOR, _)
        for _ in destructor_points:
            game_state.attempt_spawn(DESTRUCTOR, _)

    def build_reactive_defense(self, game_state):
        """
        This function builds reactive defenses based on where the enemy scored on us from.
        We can track where the opponent scored by looking at events in action frames 
        as shown in the on_action_frame function
        """

        def euclidean_distance(x1,y1,x2,y2):
            return ((x1 - x2) ** 2 + (y1 - y2) ** 2) ** 0.5

        important_points = [[0, 13], [1, 13], [2, 13], [25, 13], [26, 13], [27, 13], [5, 10], [22, 10], [8, 7], [19, 7], [11, 4], [16, 4], [12, 3], [15, 3]]
        important_points += [[3, 12], [24, 12], [4, 11], [23, 11], [6, 9], [21, 9], [7, 8], [20, 8], [9, 6], [18, 6], [10, 5], [17, 5]]

        czech_republic_black_sites = [[10, 3], [11, 3], [16, 3], [17, 3], [11, 2], [12, 2], [13, 2], [14, 2], [15, 2], [16, 2], [12, 1], [13, 1], [14, 1], [15, 1], [13, 0], [14, 0]]

        for location in self.scored_on_locations:
            # Build destructor one space above so that it doesn't block our own edge spawn locations
            for point in important_points:
                if euclidean_distance(location[0], location[1], point[0], point[1]) < 4: # some arbitrary threshold idk
                    if point not in czech_republic_black_sites:
                        game_state.attempt_spawn(DESTRUCTOR, point)
                    if [point[0], point[1] - 1] not in czech_republic_black_sites:
                        game_state.attempt_spawn(DESTRUCTOR, [point[0], point[1] - 1])

        self.build_triangle_funnel(game_state, self.pick_defense_side(game_state))

    def get_nice_spawn(self, game_state):
        """returns a nice fukn spawn"""
        right_last =  [14, 0]
        left_last = [13, 0]
        for plausible in [[19, 5], [18, 4], [17, 3], [16, 2], [15, 1]][::-1]:
            if game_state.contains_stationary_unit(plausible):
                right_last = plausible
            else:
                break
        for plausible in [[8, 5], [9, 4], [10, 3], [11, 2], [12, 1]][::-1]:
            if game_state.contains_stationary_unit(plausible):
                left_last = plausible
            else:
                break
        return (left_last, right_last)

    def pick_defense_side(self, game_state):
        lefts = 0
        rights = 0
        for coordinate in self.scored_on_locations:
            if coordinate[0] <= 13:
                lefts += 1
            elif coordinate[0] >= 14:
                rights += 1
        if lefts > rights:
            return 'left'
        elif rights > lefts:
            return 'right'
        else:
            return 'center'

    def pick_attack_side(self, game_state):
        left_coords = [[4, 18], [5, 18], [3, 17], [4, 17], [5, 17], [6, 17], [2, 16], [3, 16], [4, 16], [5, 16], [6, 16], [1, 15], [2, 15], [3, 15],
         [4, 15], [5, 15], [6, 15], [0, 14], [1, 14], [2, 14], [3, 14], [4, 14], [5, 14], [6, 14]]
        
        right_coords = [[22, 18], [23, 18], [21, 17], [22, 17], [23, 17], [24, 17], [21, 16], [22, 16], [23, 16], [24, 16], [25, 16], [21, 15], [22, 15], [23, 15],
        [24, 15], [25, 15], [26, 15], [21, 14], [22, 14], [23, 14], [24, 14], [25, 14], [26, 14], [27, 14]]

        mid_coords = [[13, 27], [14, 27], [12, 26], [13, 26], [14, 26], [15, 26], [11, 25], [12, 25], [13, 25], [14, 25], [15, 25], [16, 25], [10, 24], [11, 24], [12, 24], [13, 24], [14, 24], [15, 24], [16, 24], [17, 24], [9, 23], [10, 23], [11, 23], [12, 23], [13, 23], [14, 23], [15, 23], [16, 23], [17, 23], [18, 23], [8, 22], [9, 22], [10, 22], [11, 22], [12, 22], [13, 22], [14, 22], [15, 22], [16, 22], [17, 22], [18, 22], [19, 22], [9, 21], [10, 21], [11, 21], [12, 21], [13, 21], [14, 21], [15, 21], [16, 21], [17, 21], [18, 21], [10, 20], [11, 20], [12, 20], [13, 20], [14, 20], [15, 20], [16, 20], [17, 20], [11, 19], [12, 19], [13, 19], [14, 19], [15, 19], [16, 19], [12, 18], [13, 18], [14, 18], [15, 18], [13, 17], [14, 17]]

        left_count = 0
        for coord in left_coords:
            units = game_state.game_map[coord[0], coord[1]]
            for unit in units:
                left_count += unit.damage_i * unit.range

        right_count = 0
        for coord in right_coords:
            units = game_state.game_map[coord[0], coord[1]]
            for unit in units:
                right_count += unit.damage_i * unit.range

        mid_count = 0
        for coord in mid_coords:
            units = game_state.game_map[coord[0], coord[1]]
            for unit in units:
                mid_count += unit.damage_i * unit.range

        min_count = min(left_count, right_count, mid_count)

        if (min_count == left_count):
            return "LEFT"
        elif (min_count == right_count):
            return "RIGHT"
        else:
            return "MID"
        
    def stall_with_scramblers(self, game_state):
        """
        Send out Scramblers at random locations to defend our base from enemy moving units.
        """
        # We can spawn moving units on our edges so a list of all our edge locations
        friendly_edges = game_state.game_map.get_edge_locations(game_state.game_map.BOTTOM_LEFT) + game_state.game_map.get_edge_locations(game_state.game_map.BOTTOM_RIGHT)
        
        # Remove locations that are blocked by our own firewalls 
        # since we can't deploy units there.
        deploy_locations = self.filter_blocked_locations(friendly_edges, game_state)
        
        # While we have remaining bits to spend lets send out scramblers randomly.
        left, right = self.get_nice_spawn(game_state)
        game_state.attempt_spawn(SCRAMBLER, left, n=int(self.min_ping_threshold/6))
        game_state.attempt_spawn(SCRAMBLER, right, n=int(self.min_ping_threshold/6))

    def emp_line_strategy(self, game_state):
        """
        Build a line of the cheapest stationary unit so our EMP's can attack from long range.
        """
        # First let's figure out the cheapest unit
        # We could just check the game rules, but this demonstrates how to use the GameUnit class
        stationary_units = [FILTER, DESTRUCTOR, ENCRYPTOR]
        cheapest_unit = FILTER
        for unit in stationary_units:
            unit_class = gamelib.GameUnit(unit, game_state.config)
            if unit_class.cost < gamelib.GameUnit(cheapest_unit, game_state.config).cost:
                cheapest_unit = unit

        # Now let's build out a line of stationary units. This will prevent our EMPs from running into the enemy base.
        # Instead they will stay at the perfect distance to attack the front two rows of the enemy base.
        for x in range(27, 5, -1):
            game_state.attempt_spawn(cheapest_unit, [x, 11])

        # Now spawn EMPs next to the line
        # By asking attempt_spawn to spawn 1000 units, it will essentially spawn as many as we have resources for
        game_state.attempt_spawn(EMP, [24, 10], 1000)

    def least_damage_spawn_location(self, game_state, location_options):
        """
        This function will help us guess which location is the safest to spawn moving units from.
        It gets the path the unit will take then checks locations on that path to 
        estimate the path's damage risk.
        """
        damages = []
        # Get the damage estimate each path will take
        for location in location_options:
            path = game_state.find_path_to_edge(location)
            damage = 0
            for path_location in path:
                # Get number of enemy destructors that can attack the final location and multiply by destructor damage
                damage += len(game_state.get_attackers(path_location, 0)) * gamelib.GameUnit(DESTRUCTOR, game_state.config).damage
            damages.append(damage)
        
        # Now just return the location that takes the least damage
        return location_options[damages.index(min(damages))]      

    def detect_enemy_unit(self, game_state, unit_type=None, valid_x = None, valid_y = None):
        total_units = 0
        for location in game_state.game_map:
            if game_state.contains_stationary_unit(location):
                for unit in game_state.game_map[location]:
                    if unit.player_index == 1 and (unit_type is None or unit.unit_type == unit_type) and (valid_x is None or location[0] in valid_x) and (valid_y is None or location[1] in valid_y):
                        total_units += 1
        return total_units
        
    def filter_blocked_locations(self, locations, game_state):
        filtered = []
        for location in locations:
            if not game_state.contains_stationary_unit(location):
                filtered.append(location)
        return filtered

    def on_action_frame(self, turn_string):
        """
        This is the action frame of the game. This function could be called 
        hundreds of times per turn and could slow the algo down so avoid putting slow code here.
        Processing the action frames is complicated so we only suggest it if you have time and experience.
        Full doc on format of a game frame at: https://docs.c1games.com/json-docs.html
        """
        # Let's record at what position we get scored on
        state = json.loads(turn_string)
        events = state["events"]
        breaches = events["breach"]
        for breach in breaches:
            location = breach[0]
            unit_owner_self = True if breach[4] == 1 else False
            # When parsing the frame data directly, 
            # 1 is integer for yourself, 2 is opponent (StarterKit code uses 0, 1 as player_index instead)
            if not unit_owner_self:
                gamelib.debug_write("Got scored on at: {}".format(location))
                self.scored_on_locations.append(location)
                gamelib.debug_write("All locations: {}".format(self.scored_on_locations))


if __name__ == "__main__":
    algo = AlgoStrategy()
    algo.start()
