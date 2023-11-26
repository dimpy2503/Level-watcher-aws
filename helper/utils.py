import csv
import datetime
import json
import os


class DatetimeEncoder(json.JSONEncoder):
    def default(self, obj):
        try:
            return super().default(obj)
        except TypeError:
            return str(obj)


def warningMessege(messege):
    return {'<div class="alert alert-danger" role="alert">' + messege + '</div>'}


def successMessege(messege):
    return '<div class="alert alert-success" role="alert">' + messege + '</div>'


def writeJson(data, file_name):
    print('writeJson', data)
    file_path = file_name + ".json"
    with open(file_path, 'w') as json_file:
        json.dump(data, json_file, indent=4, cls=DatetimeEncoder)


def readJson(file_name):
    file_path = file_name + ".json"
    if os.path.exists(file_path):
        try:

            with open(file_path, 'r') as json_file:
                loaded_data = json.load(json_file)

            return loaded_data
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON from {file_name}.json: {str(e)}")
            return None
    else:
        return False


def readFile(file_path):
    if os.path.exists(file_path):
        try:
            data = []
            with open(file_path, newline='') as csvfile:
                csv_reader = csv.DictReader(csvfile)
                for row in csv_reader:
                    data.append(row)
            return data
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON from {file_path} {str(e)}")
            return None
    else:
        return False


def calculate_pivot_points_levels_4(high, low, close):
    pivot = round((high + low + close) / 3, 2)
    support1 = round((2 * pivot) - high, 2)
    support2 = round(pivot - (high - low), 2)
    support3 = round(support2 - (high - low), 2)
    support4 = round(support3 - (high - low), 2)
    resistance1 = round((2 * pivot) - low, 2)
    resistance2 = round(pivot + (high - low), 2)
    resistance3 = round(resistance2 + (high - low), 2)
    resistance4 = round(resistance3 + (high - low), 2)

    pivot_points = {
        "R4": resistance4,
        "R3": resistance3,
        "R2": resistance2,
        "R1": resistance1,
        "PP": pivot,
        "S1": support1,
        "S2": support2,
        "S3": support3,
        "S4": support4,
    }
    # pivot_points = {
    #     'R4': 45200,
    #     'R3': 44900,
    #     'R2': 44500,
    #     'R1': 44300,
    #     'PP': 44200,
    #     'S1': 44000,
    #     'S2': 43800,
    #     'S3': 43500,
    #     'S4': 43100
    # }
    return pivot_points

# # Example usage:
# high = 44408.55
# low = 44164.55
# close = 44201.7
#
# result = calculate_pivot_points_levels_4(high, low, close)
#
# for key, value in result.items():
#     print(f"{key}: {value}")
