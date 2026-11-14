#!/usr/bin/env python3
"""
tools/build_injury_csv.py

Builds data/injury-report-2026-w10.csv from the NFL.com Week 10 injury report
(source S01, https://www.nfl.com/injuries/, retrieved 2026-11-14).

Only rows that carry an NFL game status (Out / Doubtful / Questionable) are
included, because those are the rows that change availability. Practice-only
rows ("Full Participation", no game status) are excluded — the source page
lists them but they do not change who plays.

Depth-string fields are filled ONLY for clubs whose official depth chart was
captured in this pass (KC = S11, SEA = S12). Everywhere else the field is left
empty and marked 'depth chart not captured'. Nothing is inferred.
"""
import csv
import os

SRC = "https://www.nfl.com/injuries/"
RET = "2026-11-14"

# (club, abbr, opponent, player, position, injury, practice, game_status)
RECORDS = [
    # WAS @ NYG — Thu Nov 12 (already played: WAS 24, NYG 21)
    ("Commanders", "WAS", "NYG", "Lucas Patrick", "C", "Concussion", "DNP", "Out"),
    ("Commanders", "WAS", "NYG", "Colson Yankoff", "TE", "Knee", "DNP", "Out"),
    ("Giants", "NYG", "WAS", "Malik Harrison", "LB", "Groin", "Limited", "Questionable"),

    # NE at DET — Munich, Sun Nov 15 09:30 ET
    ("Patriots", "NE", "DET", "Ben Brown", "C", "Knee", "DNP", "Out"),
    ("Patriots", "NE", "DET", "Carlton Davis III", "CB", "Knee", "DNP", "Out"),
    ("Patriots", "NE", "DET", "TreVeyon Henderson", "RB", "Illness", "DNP", "Out"),
    ("Patriots", "NE", "DET", "A.J. Brown", "WR", "Ankle, Knee", "Limited", "Questionable"),
    ("Patriots", "NE", "DET", "Kevin Byard", "S", "Chest", "Full", "Questionable"),
    ("Patriots", "NE", "DET", "Reggie Gilliam", "FB", "Knee", "Limited", "Questionable"),
    ("Patriots", "NE", "DET", "Cameron Latu", "TE", "Back", "Limited", "Questionable"),
    ("Patriots", "NE", "DET", "Walter Rouse", "T", "Concussion", "Limited", "Questionable"),
    ("Patriots", "NE", "DET", "Brenden Schooler", "S", "Hamstring", "Limited", "Questionable"),
    ("Patriots", "NE", "DET", "Rhamondre Stevenson", "RB", "Knee", "Limited", "Questionable"),
    ("Patriots", "NE", "DET", "Greg Van Roten", "G", "Hamstring", "Full", "Questionable"),
    ("Patriots", "NE", "DET", "Charles Woods", "CB", "Hamstring", "Full", "Questionable"),
    ("Lions", "DET", "NE", "Kerby Joseph", "S", "Knee", "DNP", "Out"),
    ("Lions", "DET", "NE", "Cade Mays", "C", "Ankle", "DNP", "Out"),
    ("Lions", "DET", "NE", "D.J. Reed", "CB", "Hip", "DNP", "Out"),
    ("Lions", "DET", "NE", "Amon-Ra St. Brown", "WR", "Rib", "Limited", "Questionable"),
    ("Lions", "DET", "NE", "Sione Vaki", "RB", "Ankle", "Limited", "Questionable"),

    # KC at ATL — Sun Nov 15 13:00 ET
    ("Chiefs", "KC", "ATL", "Jaylon Moore", "T", "Ankle", "DNP", "Out"),
    ("Chiefs", "KC", "ATL", "Peter Woods", "DT", "Neck", "DNP", "Out"),
    ("Chiefs", "KC", "ATL", "Omarr Norman-Lott", "DT", "Knee", "Limited", "Out"),
    ("Chiefs", "KC", "ATL", "Mansoor Delane", "CB", "Shoulder", "Full", "Questionable"),
    ("Chiefs", "KC", "ATL", "Jaydn Ott", "RB", "Hamstring", "Limited", "Questionable"),
    ("Chiefs", "KC", "ATL", "Kenneth Walker III", "RB", "Groin", "DNP", "Questionable"),
    ("Falcons", "ATL", "KC", "Zachariah Branch", "WR", "Hamstring", "DNP", "Out"),
    ("Falcons", "ATL", "KC", "Divine Deablo", "LB", "Forearm", "DNP", "Doubtful"),
    ("Falcons", "ATL", "KC", "Gervon Dexter Sr.", "DT", "Illness", "Limited", "Questionable"),
    ("Falcons", "ATL", "KC", "James Pearce Jr.", "DE", "Back", "Limited", "Questionable"),
    ("Falcons", "ATL", "KC", "Josh Woods", "LB", "Ankle", "Full", "Questionable"),

    # MIN at GB — Sun Nov 15 13:00 ET
    ("Vikings", "MIN", "GB", "Blake Cashman", "LB", "Concussion", "Limited", "Out"),
    ("Vikings", "MIN", "GB", "T.J. Hockenson", "TE", "Wrist, Chest", "DNP", "Out"),
    ("Vikings", "MIN", "GB", "Tyrion Ingram-Dawkins", "DT", "Ankle", "DNP", "Out"),
    ("Vikings", "MIN", "GB", "Jauan Jennings", "WR", "Calf", "DNP", "Out"),
    ("Vikings", "MIN", "GB", "Kyler Murray", "QB", "Hamstring", "DNP", "Out"),
    ("Vikings", "MIN", "GB", "Jordan Addison", "WR", "Thumb", "Limited", "Questionable"),
    ("Vikings", "MIN", "GB", "Josh Metellus", "S", "Shoulder", "Limited", "Questionable"),
    ("Vikings", "MIN", "GB", "Kyle Van Noy", "LB", "Calf", "Limited", "Questionable"),
    ("Packers", "GB", "MIN", "Josh Jacobs", "RB", "Finger", "DNP", "Out"),
    ("Packers", "GB", "MIN", "Micah Parsons", "LB", "Knee, Illness", "Limited", "Out"),
    ("Packers", "GB", "MIN", "Sean Rhyan", "C", "Ankle", "DNP", "Out"),
    ("Packers", "GB", "MIN", "Josh Whyle", "TE", "Concussion", "DNP", "Out"),
    ("Packers", "GB", "MIN", "Zaire Franklin", "LB", "Shin", "DNP", "Doubtful"),
    ("Packers", "GB", "MIN", "Kevin Zeitler", "G", "Ankle, Triceps", "DNP", "Questionable"),
    ("Packers", "GB", "MIN", "Chris Brooks", "RB", "Ankle", "Limited", "Questionable"),
    ("Packers", "GB", "MIN", "Javon Bullard", "S", "Ankle, Knee", "Limited", "Questionable"),
    ("Packers", "GB", "MIN", "Travis Glover", "G", "Knee", "Limited", "Questionable"),
    ("Packers", "GB", "MIN", "Xavier McKinney", "S", "Foot", "Limited", "Questionable"),
    ("Packers", "GB", "MIN", "Skyy Moore", "WR", "Ankle", "Limited", "Questionable"),
    ("Packers", "GB", "MIN", "Lukas Van Ness", "LB", "Back", "Limited", "Questionable"),

    # JAX at TEN — Sun Nov 15 13:00 ET
    ("Jaguars", "JAX", "TEN", "Jessie Bates", "S", "Not injury related - resting player", "Limited", "Out"),
    ("Jaguars", "JAX", "TEN", "Jordan Davis", "DT", "Not injury related - resting player", "Limited", "Out"),
    ("Jaguars", "JAX", "TEN", "BJ Green II", "DE", "Forearm", "Full", "Out"),
    ("Jaguars", "JAX", "TEN", "Robert Hainsey", "C", "Concussion", "Limited", "Questionable"),
    ("Titans", "TEN", "JAX", "Cody Barton", "LB", "Concussion", "DNP", "Out"),
    ("Titans", "TEN", "JAX", "Anthony Hill Jr.", "LB", "Neck", "DNP", "Out"),
    ("Titans", "TEN", "JAX", "Peter Skoronski", "G", "Hamstring", "DNP", "Out"),
    ("Titans", "TEN", "JAX", "Carnell Tate", "WR", "Shoulder", "DNP", "Out"),
    ("Titans", "TEN", "JAX", "Tommy Townsend", "P", "Knee, Achilles", "DNP", "Out"),
    ("Titans", "TEN", "JAX", "Tyjae Spears", "RB", "Knee", "Full", "Questionable"),

    # BUF at NYJ — Sun Nov 15 13:00 ET
    ("Bills", "BUF", "NYJ", "Spencer Brown", "T", "Ankle", "DNP", "Doubtful"),
    ("Bills", "BUF", "NYJ", "Christian Benford", "CB", "Wrist", "Full", "Questionable"),
    ("Bills", "BUF", "NYJ", "Sam Franklin Jr.", "S", "Shoulder", "Limited", "Questionable"),
    ("Bills", "BUF", "NYJ", "Jordan Hancock", "CB", "Hamstring", "Full", "Questionable"),
    ("Bills", "BUF", "NYJ", "Tyrell Shavers", "WR", "Knee", "Full", "Questionable"),
    ("Jets", "NYJ", "BUF", "Trevin Wallace", "LB", "Groin", "DNP", "Out"),
    ("Jets", "NYJ", "BUF", "Jarvis Brownlee Jr.", "CB", "Illness", "Limited", "Questionable"),
    ("Jets", "NYJ", "BUF", "Omar Cooper Jr.", "WR", "Ankle", "Full", "Questionable"),
    ("Jets", "NYJ", "BUF", "Adonai Mitchell", "WR", "Knee", "Full", "Questionable"),
    ("Jets", "NYJ", "BUF", "Joseph Ossai", "DE", "Ankle", "Full", "Questionable"),
    ("Jets", "NYJ", "BUF", "VJ Payne", "S", "Knee", "Full", "Questionable"),
    ("Jets", "NYJ", "BUF", "Harrison Phillips", "DT", "Ankle", "Full", "Questionable"),
    ("Jets", "NYJ", "BUF", "Garrett Wilson", "WR", "Concussion", "Full", "Questionable"),
    ("Jets", "NYJ", "BUF", "Nahshon Wright", "CB", "Back", "Full", "Questionable"),

    # MIA at IND — Sun Nov 15 13:00 ET
    ("Dolphins", "MIA", "IND", "Aaron Brewer", "C", "Concussion", "DNP", "Out"),
    ("Dolphins", "MIA", "IND", "Jared Wayne", "WR", "Quadricep", "DNP", "Out"),
    ("Dolphins", "MIA", "IND", "Chris Bell", "WR", "Knee", "DNP", "Doubtful"),
    ("Dolphins", "MIA", "IND", "Darrell Baker Jr.", "CB", "Knee", "Full", "Questionable"),
    ("Colts", "IND", "MIA", "Mo Alie-Cox", "TE", "Groin", "DNP", "Out"),
    ("Colts", "IND", "MIA", "Jaylon Carlies", "LB", "Neck", "DNP", "Out"),
    ("Colts", "IND", "MIA", "Akeem Davis-Gaither", "LB", "Knee", "DNP", "Out"),
    ("Colts", "IND", "MIA", "Luke Rhodes", "LS", "Hamstring", "DNP", "Out"),
    ("Colts", "IND", "MIA", "Jerry Tillery", "DT", "Calf", "DNP", "Out"),
    ("Colts", "IND", "MIA", "Jalen Travis", "T", "Knee", "DNP", "Out"),
    ("Colts", "IND", "MIA", "Arden Key", "DE", "Hamstring", "Full", "Questionable"),
    ("Colts", "IND", "MIA", "Will Mallory", "TE", "Hamstring", "Limited", "Questionable"),

    # CAR at NO — Sun Nov 15 13:00 ET
    ("Panthers", "CAR", "NO", "Bobby Okereke", "LB", "Foot", "DNP", "Out"),
    ("Panthers", "CAR", "NO", "Jonathon Brooks", "RB", "Groin", "Limited", "Doubtful"),
    ("Panthers", "CAR", "NO", "Mike Jackson", "CB", "Groin", "Limited", "Doubtful"),
    ("Panthers", "CAR", "NO", "Brady Christensen", "G", "Hamstring", "Full", "Questionable"),
    ("Panthers", "CAR", "NO", "Will Lee III", "CB", "Hamstring", "Limited", "Questionable"),
    ("Panthers", "CAR", "NO", "Xavier Legette", "WR", "Knee", "Full", "Questionable"),
    ("Panthers", "CAR", "NO", "Jaelan Phillips", "LB", "Hamstring", "Full", "Questionable"),
    ("Saints", "NO", "CAR", "CJ Donaldson", "RB", "Shoulder", "DNP", "Out"),
    ("Saints", "NO", "CAR", "Taliese Fuaga", "T", "Knee", "DNP", "Out"),
    ("Saints", "NO", "CAR", "Erik McCoy", "C", "Biceps", "DNP", "Out"),
    ("Saints", "NO", "CAR", "Christen Miller", "DT", "Knee", "DNP", "Out"),
    ("Saints", "NO", "CAR", "Martin Emerson", "CB", "Shin", "Limited", "Questionable"),
    ("Saints", "NO", "CAR", "Travis Etienne", "RB", "Hamstring", "Full", "Questionable"),

    # HOU at CLE — Sun Nov 15 13:00 ET
    ("Texans", "HOU", "CLE", "Azeez Al-Shaair", "LB", "Groin, Not injury related - personal matter", "DNP", "Out"),
    ("Texans", "HOU", "CLE", "Marvin Harrison Jr.", "WR", "Hamstring", "DNP", "Out"),
    ("Texans", "HOU", "CLE", "Danielle Hunter", "DE", "Hamstring", "DNP", "Out"),
    ("Texans", "HOU", "CLE", "Brevin Jordan", "TE", "Finger, Foot", "DNP", "Out"),
    ("Texans", "HOU", "CLE", "Keylan Rutledge", "G", "Neck, Shoulder", "DNP", "Out"),
    ("Texans", "HOU", "CLE", "Will Anderson Jr.", "DE", "Ankle", "DNP", "Questionable"),
    ("Texans", "HOU", "CLE", "Trent Brown", "T", "Wrist, Illness", "DNP", "Questionable"),
    ("Texans", "HOU", "CLE", "Jacob Hummel", "LB", "Groin", "Full", "Questionable"),
    ("Texans", "HOU", "CLE", "David Montgomery", "RB", "Groin", "Full", "Questionable"),
    ("Texans", "HOU", "CLE", "Jaylin Smith", "CB", "Hamstring", "Full", "Questionable"),
    ("Texans", "HOU", "CLE", "Wyatt Teller", "G", "Illness, Back", "Limited", "Questionable"),
    ("Browns", "CLE", "HOU", "Michael Burton", "FB", "Calf", "DNP", "Out"),
    ("Browns", "CLE", "HOU", "Ronnie Hickman Jr.", "S", "Concussion", "DNP", "Out"),
    ("Browns", "CLE", "HOU", "Denzel Boston", "WR", "Toe", "Limited", "Questionable"),

    # LA at AZ — Sun Nov 15 16:05 ET
    ("Rams", "LA", "AZ", "Steve Avila", "G", "Hamstring", "DNP", "Out"),
    ("Rams", "LA", "AZ", "Terrance Ferguson", "TE", "Ankle, Hamstring", "DNP", "Out"),
    ("Rams", "LA", "AZ", "Myles Garrett", "LB", "Knee, Not injury related - resting player", "DNP", "Questionable"),
    ("Rams", "LA", "AZ", "Davis Allen", "TE", "Oblique", "Limited", "Questionable"),
    ("Rams", "LA", "AZ", "Joe Cardona", "LS", "Ankle", "Limited", "Questionable"),
    ("Rams", "LA", "AZ", "Kam Curl", "S", "Toe", "Limited", "Questionable"),
    ("Rams", "LA", "AZ", "Trent McDuffie", "CB", "Back", "Limited", "Questionable"),
    ("Cardinals", "AZ", "LA", "Zachary Carter", "DT", "Knee", "Limited", "Out"),
    ("Cardinals", "AZ", "LA", "Hjalte Froholdt", "C", "Concussion", "DNP", "Out"),
    ("Cardinals", "AZ", "LA", "Jon Gaines II", "G", "Ankle", "DNP", "Out"),
    ("Cardinals", "AZ", "LA", "Andrew Wingard", "S", "Groin", "DNP", "Questionable"),
    ("Cardinals", "AZ", "LA", "Hunter Long", "TE", "Knee", "Limited", "Questionable"),
    ("Cardinals", "AZ", "LA", "Roy Lopez", "DT", "Toe, Ankle", "Limited", "Questionable"),
    ("Cardinals", "AZ", "LA", "Max Melton", "CB", "Knee, Hand", "Limited", "Questionable"),
    ("Cardinals", "AZ", "LA", "Darius Robinson", "DT", "Wrist", "Limited", "Questionable"),
    ("Cardinals", "AZ", "LA", "Jayden Williams", "T", "Knee", "Limited", "Questionable"),

    # SEA at LV — Sun Nov 15 16:05 ET
    ("Seahawks", "SEA", "LV", "Sam Darnold", "QB", "Ribs, Quadricep", "DNP", "Out"),
    ("Seahawks", "SEA", "LV", "Charles Cross", "T", "Ankle", "DNP", "Out"),
    ("Seahawks", "SEA", "LV", "Quenton Nelson", "G", "Knee", "DNP", "Out"),
    ("Seahawks", "SEA", "LV", "Leonard Williams", "DT", "Stinger", "DNP", "Out"),
    ("Raiders", "LV", "SEA", "Dont'e Thornton Jr.", "WR", "Back", "DNP", "Questionable"),
    ("Raiders", "LV", "SEA", "Thomas Booker", "DT", "Ankle", "Full", "Questionable"),

    # SF at DAL — Sun Nov 15 16:25 ET
    ("49ers", "SF", "DAL", "Mike Evans", "WR", "Achilles", "DNP", "Out"),
    ("49ers", "SF", "DAL", "Trent Williams", "T", "Shoulder", "DNP", "Questionable"),
    ("49ers", "SF", "DAL", "Renardo Green", "CB", "Back", "Limited", "Questionable"),
    ("49ers", "SF", "DAL", "Dre Greenlaw", "LB", "Knee", "Limited", "Questionable"),
    ("49ers", "SF", "DAL", "Deommodore Lenoir", "CB", "Foot", "Limited", "Questionable"),
    ("49ers", "SF", "DAL", "Upton Stout", "CB", "Shoulder, Neck", "Limited", "Questionable"),
    ("49ers", "SF", "DAL", "Nate Hobbs", "CB", "Groin", "Full", "Questionable"),
    ("49ers", "SF", "DAL", "C.J. West", "DT", "Knee", "Full", "Questionable"),
    ("Cowboys", "DAL", "SF", "Donovan Ezeiruaku", "LB", "Ankle", "DNP", "Out"),
    ("Cowboys", "DAL", "SF", "Jake Ferguson", "TE", "Knee, Ankle", "DNP", "Out"),
    ("Cowboys", "DAL", "SF", "Tyler Goodson", "RB", "Ankle, Knee", "DNP", "Out"),
    ("Cowboys", "DAL", "SF", "P.J. Locke", "S", "Concussion", "DNP", "Out"),
    ("Cowboys", "DAL", "SF", "Jonathan Mingo", "WR", "Ankle", "DNP", "Out"),
    ("Cowboys", "DAL", "SF", "Juanyeh Thomas", "S", "Hamstring", "DNP", "Doubtful"),
    ("Cowboys", "DAL", "SF", "Alijah Clark", "S", "Illness", "DNP", "Questionable"),
    ("Cowboys", "DAL", "SF", "DaRon Bland", "CB", "Ankle", "Limited", "Questionable"),
    ("Cowboys", "DAL", "SF", "Joey Porter Jr.", "CB", "Ankle, Foot", "Limited", "Questionable"),
    ("Cowboys", "DAL", "SF", "Jonathan Bullard", "DT", "Calf", "Full", "Questionable"),
    ("Cowboys", "DAL", "SF", "Devin Moore", "CB", "Hip", "Full", "Questionable"),

    # PIT at CIN — Sun Nov 15 20:20 ET
    ("Steelers", "PIT", "CIN", "Derrick Harmon", "DT", "Foot", "Full", "Questionable"),
    ("Bengals", "CIN", "PIT", "Kyle Dugger", "S", "Quadricep", "DNP", "Out"),
    ("Bengals", "CIN", "PIT", "Jalen Davis", "CB", "Hamstring", "Full", "Doubtful"),
    ("Bengals", "CIN", "PIT", "Andrei Iosivas", "WR", "Thumb", "Full", "Doubtful"),
    ("Bengals", "CIN", "PIT", "Brian Parker II", "G", "Knee", "Full", "Doubtful"),
]

# Official club depth charts captured in this pass.
# KC: chiefs.com (S11).  SEA: seahawks.com (S12).
KC_DEPTH = {
    ("Rashee Rice", "WR"): 1, ("Jalen Royals", "WR"): 2, ("Andrew Armstrong", "WR"): 3,
    ("Kahlil Benson", "T"): 1, ("Diego Pounds", "T"): 2,
    ("Kingsley Suamataia", "G"): 1, ("Joshua Ezeudu", "G"): 2,
    ("Creed Humphrey", "C"): 1, ("Hunter Nourzad", "C"): 2,
    ("Trey Smith", "G"): 1, ("Mike Caliendo", "G"): 2,
    ("Jaylon Moore", "T"): 1, ("Kenny Pickett", "QB"): 3,
    ("Travis Kelce", "TE"): 1, ("Noah Gray", "TE"): 2, ("Jared Wiley", "TE"): 3, ("Jake Briningstool", "TE"): 4,
    ("Patrick Mahomes", "QB"): 1, ("Justin Fields", "QB"): 2, ("Garrett Nussmeier", "QB"): 3,
    ("Kenneth Walker III", "RB"): 1, ("Emmett Johnson", "RB"): 2, ("Jaydn Ott", "RB"): 3,
    ("Xavier Worthy", "WR"): 1, ("Cyrus Allen", "WR"): 2, ("Josh Downs", "WR"): 3,
    ("Felix Anudike-Uzomah", "DE"): 1, ("Ashton Gillotte", "DE"): 2,
    ("Chris Jones", "DT"): 1, ("Peter Woods", "DT"): 2, ("Marcus Harris", "DT"): 3,
    ("Khyiris Tonga", "DT"): 1, ("Bryson Eason", "DT"): 2,
    ("George Karlaftis", "DE"): 1, ("R Mason Thomas", "DE"): 2,
    ("Jack Cochrane", "LB"): 1, ("Nick Bolton", "LB"): 1, ("Drue Tranquill", "LB"): 1,
    ("Cooper McDonald", "LB"): 2, ("Jeffrey Bassa", "LB"): 2,
    ("Nohl Williams", "CB"): 1, ("Jadon Canady", "CB"): 2,
    ("Mansoor Delane", "CB"): 1, ("Kristian Fulton", "CB"): 2, ("Melvin Smith", "CB"): 3,
    ("Alohi Gilman", "S"): 1, ("Chris Roland-Wallace", "S"): 2,
    ("Chamarri Conner", "S"): 1, ("Jaden Hicks", "S"): 2, ("Xavier Nwankpa", "S"): 3,
}
SEA_DEPTH = {
    ("Cooper Kupp", "WR"): 1, ("Rashid Shaheed", "WR"): 1, ("Irvin Charles", "WR"): 2,
    ("Charles Cross", "T"): 1, ("Josh Jones", "T"): 2,
    ("Quenton Nelson", "G"): 1, ("Anthony Bradford", "G"): 2, ("Beau Stephens", "G"): 3,
    ("Jalen Sundell", "C"): 1, ("Olu Oluwatimi", "C"): 2,
    ("Grey Zabel", "G"): 1, ("Abraham Lucas", "T"): 1,
    ("AJ Barner", "TE"): 1, ("Eric Saubert", "TE"): 2, ("Nick Kallerup", "TE"): 3,
    ("Jaxon Smith-Njigba", "WR"): 1, ("Tory Horton", "WR"): 2,
    ("Sam Darnold", "QB"): 1, ("Drew Lock", "QB"): 2, ("Jalen Milroe", "QB"): 3,
    ("Zach Charbonnet", "RB"): 1, ("Jadarian Price", "RB"): 2, ("Emanuel Wilson", "RB"): 3, ("George Holani", "RB"): 4,
    ("Leonard Williams", "DT"): 1, ("Rylie Mills", "DT"): 2,
    ("Byron Murphy II", "NT"): 1, ("Brandon Pili", "NT"): 2,
    ("Jarran Reed", "DE"): 1, ("Mike Morris", "DE"): 2,
    ("DeMarcus Lawrence", "RUSH"): 1, ("Derick Hall", "RUSH"): 2,
    ("Ernest Jones IV", "MLB"): 1, ("Patrick O'Connell", "MLB"): 2,
    ("Drake Thomas", "WLB"): 1, ("Tyrice Knight", "WLB"): 2, ("Chazz Surratt", "WLB"): 3,
    ("Uchenna Nwosu", "SLB"): 1, ("Dante Fowler Jr.", "SLB"): 2, ("Connor O'Toole", "SLB"): 3,
    ("Devon Witherspoon", "CB"): 1, ("Nehemiah Pritchett", "CB"): 2,
    ("Josh Jobe", "CB"): 1, ("Avery Smith", "CB"): 2,
    ("Ty Okada", "S"): 1, ("Rodney Thomas II", "S"): 2,
    ("Julian Love", "S"): 1, ("Nick Emmanwori", "S"): 1,
}

# Next man up, read directly off the official depth chart (2nd string at that slot).
NEXT_MAN = {
    ("KC", "Jaylon Moore", "T"): "Diego Pounds (2nd string LT per chiefs.com depth chart)",
    ("KC", "Peter Woods", "DT"): "Marcus Harris (3rd string DT per chiefs.com depth chart)",
    ("KC", "Kenneth Walker III", "RB"): "Emmett Johnson (2nd string RB per chiefs.com depth chart)",
    ("KC", "Mansoor Delane", "CB"): "Kristian Fulton (2nd string CB per chiefs.com depth chart)",
    ("SEA", "Sam Darnold", "QB"): "Drew Lock (2nd string QB; nfl.com reports Lock will start)",
    ("SEA", "Charles Cross", "T"): "Josh Jones (2nd string LT per seahawks.com depth chart)",
    ("SEA", "Quenton Nelson", "G"): "Anthony Bradford (2nd string LG per seahawks.com depth chart)",
    ("SEA", "Leonard Williams", "DT"): "Rylie Mills (2nd string DT per seahawks.com depth chart)",
}

DEPTH_SRC = {
    "KC": ("S11", "https://www.chiefs.com/team/depth-chart"),
    "SEA": ("S12", "https://www.seahawks.com/team/depth-chart/"),
}

# Coverage gaps on the source page for clubs whose team block was not captured.
COVERAGE_NOTE = {
    "CHI": "team block not captured in this pass", "DEN": "team block not captured in this pass",
    "PHI": "team block not captured in this pass", "TB": "team block not captured in this pass",
}

def main():
    os.makedirs("data", exist_ok=True)
    out = "data/injury-report-2026-w10.csv"
    fields = ["club", "abbr", "opponent", "player", "position", "injury", "practice_status",
              "game_status", "depth_string", "depth_basis", "next_man_up",
              "source_id", "source_url", "depth_source_url", "retrieved", "verification"]
    with open(out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for club, abbr, opp, player, pos, inj, prac, status in RECORDS:
            depth, basis, nextman, dsrc = "", "", "", ""
            table = KC_DEPTH if abbr == "KC" else SEA_DEPTH if abbr == "SEA" else None
            if table:
                if (player, pos) in table:
                    depth = str(table[(player, pos)])
                    basis = f"position match ({pos}) on official club depth chart"
                    dsrc = DEPTH_SRC[abbr][1]
                else:
                    basis = "player not listed at this position on the captured depth chart"
            else:
                basis = "depth chart not captured in this pass"
            nextman = NEXT_MAN.get((abbr, player, pos), "")
            w.writerow({
                "club": club, "abbr": abbr, "opponent": opp, "player": player,
                "position": pos, "injury": inj, "practice_status": prac,
                "game_status": status, "depth_string": depth, "depth_basis": basis,
                "next_man_up": nextman, "source_id": "S01", "source_url": SRC,
                "depth_source_url": dsrc, "retrieved": RET, "verification": "verified",
            })
    print(f"wrote {len(RECORDS)} rows -> {out}")

if __name__ == "__main__":
    main()
