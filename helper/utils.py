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
    return { '<div class="alert alert-danger" role="alert">' + messege + '</div>'}


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
