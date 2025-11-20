import copy

from elastalert.ruletypes import EventWindow
from elastalert.ruletypes import RuleType

from elastalert.util import (dt_to_ts, elastalert_logger, hashable,
                             lookup_es_key, new_get_event_ts, pretty_ts,
                             ts_to_dt)

class CorrelationRule(RuleType):
    """
    A rule that matches if num_events sequences of correlated_events (in order
    of configured position) occur within a timeframe.
    """
    required_options = set(['num_events', 'timeframe', 'correlated_events'])

    def __init__(self, *args):
        super(CorrelationRule, self).__init__(*args)
        self.ts_field = self.rules.get('timestamp_field', '@timestamp')
        self.get_ts = new_get_event_ts(self.ts_field)
        self.attach_related = self.rules.get('attach_related', True)

    def add_data(self, data):
        """
        This function is called each time Elasticsearch is queried. It will
        check for the configured correlation of events each time it loops over
        an event in the passed in data. It is mostly identical to the add_data
        function from the FrequencyRule class.
        """
        if 'query_key' in self.rules:
            qk = self.rules['query_key']
        else:
            qk = None

        for event in data:
            if qk:
                key = hashable(lookup_es_key(event, qk))
            else:
                # If no query_key, we use the key 'all' for all events
                key = 'all'

            # Store occurrences in EventWindow objects, ordered by timestamp
            self.occurrences.setdefault(key, EventWindow(self.rules['timeframe'], getTimestamp=self.get_ts)).append((event, 1))
            # Check for correlation of events
            self.check_for_match(key, end=False)

        if key in self.occurrences:
            # Check for correlation of the events with the specified query_key
            self.check_for_match(key, end=True)

    def get_num_correlations(self, correlated_indices):
        """
        Finds the maximum number of sequential integers in a set of nested lists.
        For example, given the following lists of lists of integers:

        [[2, 4], [1, 5], [0, 3]]    returns 0 matches
        [[0, 5], [2, 10], [3, 11]]  returns 2 matches (0->2->3 and 5->10->11)
        [[0, 5], [2, 10], [1, 7]]   returns 1 match (0->2->7)

        Returns an integer that is the number of matches.
        """
        # Deep copy the passed in list of lists, to avoid modifying it
        positions_list = copy.deepcopy(correlated_indices)
        num_matches = 0
        # Sort nested lists so we can inspect positions in sequential order
        # (guarantees that the position in the first nested list that we start a
        # potentially valid sequence from is the smallest, so if no valid sequence
        # is found, there are no valid sequences left)
        for positions in positions_list:
            positions.sort()
        # Iterate at most number of positions for first event (max number matches)
        initial_positions_len = len(positions_list[0])
        for i in range(initial_positions_len):
            # A list to hold any matching positions that are part of a potentially
            # valid sequence of events. If a valid sequence is found, these
            # positions will be removed from the positions list before another
            # iteration of the loop.
            matching_positions = []
            # Check if there are any positions for the first event left
            if len(positions_list[0]) > 0:
                # Set our previous position to the first occurrence of the first
                # event, and add it to the list of matching positions
                previous_position = positions_list[0][0]
                matching_positions.append(positions_list[0][0])
                # Loop over each list in the positions_list list, skipping the
                # first one since it has no previous position
                for positions in positions_list[1:]:
                    # Assume an invalid sequence until we find a position greater
                    # than the previous position in the sequence found
                    valid_sequence = False
                    for position in positions:
                        if position > previous_position:
                            valid_sequence = True
                            previous_position = position
                            matching_positions.append(position)
                            # We can stop checking this list of positions and move
                            # on to the next one
                            break
                        else:
                            continue
                # Finished checking each nested list. If we found a valid sequence,
                # increment num_matches, remove all matched positions from the
                # positions list, and move on to the next loop iteration.
                if valid_sequence:
                    num_matches += 1
                    for i, position in enumerate(matching_positions):
                        del positions_list[i][positions_list[i].index(position)]
                # If there was no valid sequence, we've found all possible matches
                else:
                    return num_matches
        return num_matches

    def check_for_match(self, key, end=False):
        """
        Constructs a list of lists, checks for number of matches, and alerts.
        The outer list is in order of the position defined in the rule
        configuration file. The inner lists are the positions or order in the
        stream of events at which the configured correlated_events were found.
        This is passed to a function to determine the maximum possible
        correlations (ordered sequences of items from each inner list, i.e., the
        number of separate times the correlated events happened in the order
        specified by their configured positions.

        For example, if 6 events are present at self.occurrences[key], in the
        following order and with these values in the eventName field:

        StopInstances, ModifyInstanceAttribute, StopInstances, StartInstances,
        ModifyInstanceAttribute, StartInstances

        And the rule configuration specifies:

        correlated_events:
        - position: 1
          key: eventName
          value: StopInstances
        - position: 2
          key: eventName
          value: ModifyInstanceAttribute
        - position: 3
          key: eventName
          value: StartInstances

        The resulting list (correlated_event_indices) passed to the
        get_num_correlations function will be:

        [[0, 2], [1, 4], [3, 5]] 

        The number of matches returned should be 2, since 0->1->3 and 2->4->5
        are both valid sequences of events.
        """
        correlated_event_indices = []
        # Check if there are enough events for a correlation to be found
        if self.occurrences[key].count() >= len(self.rules['correlated_events']):
            # Sort events by their positions defined in rule configuration
            correlated_events = sorted(self.rules['correlated_events'], key=lambda d: d['position'])
            # For each event we're looking for, find the indices at which it
            # occurs and store them as a nested list inside the
            # correlated_event_indices list
            for correlated_event in correlated_events:
                indices = []
                for index, event in enumerate(self.occurrences[key].data):
                    # 0th index of event contains event data
                    if event[0][correlated_event['key']] == correlated_event['value']:
                        indices.append(index)
                correlated_event_indices.append(indices)
            # Check if the number of sequences of events is greater than or
            # equal to the number of events (our threshold for sending an alert)
            # defined in the rule configuration
            if self.get_num_correlations(correlated_event_indices) >= self.rules['num_events']:
                # Get data of last event in sequence and attach related events
                last_event_data = self.occurrences[key].data[-1][0]
                last_event_data['related_events'] = [data[0] for data in self.occurrences[key].data[:-1]]
                # Add match and pop this query_key's occurrences from list
                self.add_match(last_event_data)
                self.occurrences.pop(key)

    def garbage_collect(self, timestamp):
        """
        Remove all occurrence data that is beyond the timeframe away. Copied
        from the FrequencyRule class.
        """
        stale_keys = []
        for key, window in self.occurrences.items():
            if timestamp - lookup_es_key(window.data[-1][0], self.ts_field) > self.rules['timeframe']:
                stale_keys.append(key)
        list(map(self.occurrences.pop, stale_keys))

    def get_match_str(self, match):
        lt = self.rules.get('use_local_time')
        fmt = self.rules.get('custom_pretty_ts_format')
        match_ts = lookup_es_key(match, self.ts_field)
        starttime = pretty_ts(dt_to_ts(ts_to_dt(match_ts) - self.rules['timeframe']), lt, fmt)
        endtime = pretty_ts(match_ts, lt, fmt)
        message = 'At least %d sequences of events occurred between %s and %s\n\n' % (self.rules['num_events'],
                                                                                      starttime,
                                                                                      endtime)
        return message
