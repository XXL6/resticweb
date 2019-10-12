import re
import json


# class can be overriden with a custom progress tracker if needed
# as long as it has the ability to "get_current_progress"
class ProgressTracker:

    current_progress = 0.0
    regex = None
    json_key = None
    multiplier = 1
    # multi input essentially means that the value you get from the
    # string outputted by the engine process is not the actual value
    # of the current progress of the whole job.
    # An example of this can be found when a backup process is
    # started, and the backup application is outputting a completion
    # percentage for each file/folder that is being copied. If
    # multi_input is set to false in that case, then the progress
    # bar would quickly fill up and then reset for every file
    # copied which is not what we want.
    def __init__(self, multi_input=False):
        self.multi_input = multi_input

    def get_current_progress(self):
        return self.current_progress

    def set_regex(self, regex):
        self.regex = regex

    def set_json(self, json_key):
        self.json_key = json_key

    def set_multiplier(self, multiplier):
        self.multiplier = multiplier

    def get_regex(self):
        return self.regex

    def set_progress(self, input_string):
        # if multi_input is false, we can assume that the value
        # the process outputs is the completion state of the whole job
        if not self.multi_input:
            temp_progress = self.parse_progress(input_string)
            if temp_progress is not None:
                self.current_progress = temp_progress * self.multiplier
        else:
            # let's just deal with single input progresses for now
            pass

    # current progress can be set manually if the regex based
    # parsing is not wanted.
    def override_progress(self, progress):
        self.current_progress = progress

    # right now input_string is just going to be a dictionary
    # and not a string. I'll keep the name for now in case we might
    # need to parse an actual string later
    def parse_progress(self, input_string):
        # we use regex to try and parse out the potential progress strings
        # that might show up in the application
        progress_value = None

        if self.json_key:
            try:
                # json_object = json.loads(input_string)
                json_object = input_string.get(self.json_key)
                if json_object:
                    try:
                        progress_value = float(json_object)
                    except ValueError:
                        return None
            except ValueError:
                return None

        elif self.regex:
            try:
                # input_string = input_string.decode('utf-8')
                parsed_string = re.search(self.regex, input_string)
            except AttributeError:
                raise ("Attempt to set the progress was made, but regex "
                       "was not defined.")
            if parsed_string:
                try:
                    progress_value = float(parsed_string.group())
                except ValueError:
                    return None
        return progress_value

    def reset_progress(self):
        self.current_progress = 0.0


class BasicProgressTracker:
    current_progress = 0.0
    max_progress = 0

    def set_progress(self, progress):
        self.current_progress = progress
        return self.current_progress

    def set_adjusted_progress(self, progress):
        self.current_progress = (100.0 / self.max_progress) * progress
        return self.current_progress
    
    def set_max_progress(self, max_progress):
        self.max_progress = max_progress

    def increment(self):
        self.current_progress += 100.0 / self.max_progress
        return self.current_progress

    def get_current_progress(self):
        return self.current_progress


# regex based tracker of all other misc data that can be retrieved
# from a running process in real time
# example: Time Left
class DataTracker:
    # data will be stored as a list of dictionaries internally
    data_set = []

    def __init__(self):
        pass

    # set regex to None if manual setting of a value is wanted
    # pass in a json key if the engine provides an ability to output
    # that instead of regex
    def insert_tracker(self, name, json_key=None, regex=None):
        self.data_set.append(dict(name=name, regex=regex, json_key=json_key, data=None))

    # right now input_string is just going to be a dictionary
    # and not a string. I'll keep the name for now in case we might
    # need to parse an actual string later
    def update(self, input_string):
        for data in self.data_set:
            if data['regex'] is not None:
                temp = self.parse_string(data['regex'], input_string)
                # it's normal for the regex to return no value
                # in that case we just leave the data alone
                if temp is not None:
                    data['data'] = temp
            if data['json_key'] is not None:
                try:
                    # temp = json.loads(input_string)
                    data['data'] = input_string.get(data['json_key'])
                except:
                    data['data'] = None

    # returns all currently stored values in the tracker
    # the return dictionary will have the name of the data stored
    # as the key and the data stored itself as the value
    def get_data_values(self):
        if len(self.data_set) > 0:
            return_dict = {}
            for data in self.data_set:
                return_dict[data['name']] = data['data']
            return return_dict
        else:
            return None

    # values can be set manually if custom tracker is used
    # the regex in that case would be None and ignored when
    # updating other values
    def override_data(self, name, input_data):
        for data in self.data_set:
            if data['name'] == name:
                data['data'] = input_data

    def parse_string(self, regex, input_string):
        parsed_string = None
        try:
            parsed_string = re.search(regex, input_string)
        except AttributeError:
            raise ("Attempt to get data was made, but regex "
                   "was not defined.")
        if parsed_string:
            return parsed_string.group()
        else:
            return None


class ResultTracker:
    data_set = {}

    def __init__(self):
        pass

    def add_to_tracker(self, input_key, input_value):
        self.data_set[input_key] = input_value

    def is_empty(self):
        return len(self.data_set) < 1

    def get_result_dictionary(self):
        return self.data_set