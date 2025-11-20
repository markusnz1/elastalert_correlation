# ElastAlert2 Correlation Rule with Aggregation Support

A custom ElastAlert2 rule type that detects sequences of correlated events within a timeframe, with support for both simple key-value matching and advanced aggregation-based matching.

**Original Implementation**: https://github.com/jertel/elastalert2/discussions/854 by [@briandefiant](https://github.com/briandefiant)

**Enhanced with**: Aggregation support for detecting patterns like multiple failed attempts followed by success

---

## Table of Contents

- [Overview](#overview)
- [Repository Structure](#repository-structure)
- [Installation](#installation)
- [Configuration](#configuration)
  - [Basic Configuration](#basic-configuration)
  - [Regular Key-Value Matching](#regular-key-value-matching)
  - [Aggregation-Based Matching](#aggregation-based-matching)
- [Use Cases](#use-cases)
- [Examples](#examples)
- [Aggregation Types](#aggregation-types)
- [Query Syntax](#query-syntax)
- [Advanced Examples](#advanced-examples)

---

## Overview

The `CorrelationRule` detects sequences of events that occur in a specific order within a defined timeframe. It supports two types of event matching:

1. **Regular Key-Value Matching**: Match events where a specific field equals a specific value
2. **Aggregation-Based Matching**: Match based on aggregations (e.g., cardinality, count) across events matching a query

This is particularly useful for security use cases like:
- Detecting multiple failed login attempts followed by a successful login
- Identifying suspicious sequences of AWS API calls
- Tracking multi-stage attack patterns

---

## Repository Structure

This repository contains:

```
elastalert_correlation/
├── elastalert_modules/              # Python module (ready to copy)
│   ├── __init__.py                  # Module initialization
│   └── custom_rule_types.py         # CorrelationRule implementation
├── example_rules/                   # Example rule configurations
│   ├── brute_force_detection.yaml   # Brute force detection example
│   ├── aws_instance_manipulation.yaml  # AWS API sequence example
│   └── multiple_failed_attempts.yaml   # Failed attempts example
├── custom_rule_types.py             # Standalone version (for reference)
├── README.md                        # This documentation
└── .gitignore                       # Git ignore file
```

**Note**: The `elastalert_modules/` directory is the one you'll copy to your ElastAlert2 installation. The standalone `custom_rule_types.py` in the root is provided for reference only.

---

## Installation

### Step 1: Copy Module to ElastAlert2

ElastAlert2 requires custom rules to be in a proper Python module. Copy the entire `elastalert_modules/` directory from this repository to your ElastAlert2 installation:

```bash
# Clone or download this repository
git clone https://github.com/markusnz1/elastalert_correlation.git
cd elastalert_correlation

# Copy the entire module directory to your ElastAlert2 installation
cp -r elastalert_modules /path/to/elastalert2/
```

### Step 2: Verify Module Structure

Your ElastAlert2 directory should now look like this:

```
/path/to/elastalert2/
├── elastalert_modules/          # Copied from this repository
│   ├── __init__.py              # Makes it a Python module
│   └── custom_rule_types.py     # CorrelationRule implementation
└── rules/                       # Your rules directory
    └── your_rule.yaml
```

### Step 3: Copy Example Rules (Optional)

You can also copy the example rules to your ElastAlert2 rules directory:

```bash
# Copy example rules to your rules directory
cp example_rules/*.yaml /path/to/elastalert2/rules/

# Edit them to match your environment (index names, alert settings, etc.)
```

### Step 4: Reference in Rules

In your rule configuration files, reference the custom rule type using the full module path:

```yaml
type: "elastalert_modules.custom_rule_types.CorrelationRule"
```

**Note**: The quotes around the type are required when using custom rule types.

---

## Configuration

### Basic Configuration

All correlation rules require these fields:

```yaml
name: "My Correlation Rule"
type: "elastalert_modules.custom_rule_types.CorrelationRule"
index: my-index-*

# Required fields
num_events: 1                    # Minimum number of complete sequences to trigger alert
timeframe:
  minutes: 5                     # Time window for correlation
correlated_events:               # List of events to correlate (see below)
  - position: 1
    # ... event configuration ...

# Optional fields
query_key: user.name             # Group events by this field (optional)
timestamp_field: "@timestamp"    # Timestamp field (default: @timestamp)
attach_related: true             # Include related events in alert (default: true)

# Standard ElastAlert2 fields
alert: email
email: ["security@example.com"]
```

### Regular Key-Value Matching

Match events where a specific field has a specific value:

```yaml
correlated_events:
  - position: 1
    key: eventName               # Field name
    value: StopInstances         # Expected value
  - position: 2
    key: eventName
    value: ModifyInstanceAttribute
```

### Aggregation-Based Matching

Match based on aggregations across events matching a query:

```yaml
correlated_events:
  - position: 1
    type: aggregation                              # Indicates aggregation-based matching
    query: "resultType:(50097 OR 50140 OR 50126)"  # Lucene-style query
    aggregation_type: cardinality                  # Type of aggregation
    aggregation_field: resultType                  # Field to aggregate on
    aggregation_count: 3                           # Minimum count threshold
  - position: 2
    key: resultSignature
    value: SUCCESS
```

**Aggregation Parameters:**

- `type`: Must be `"aggregation"`
- `query`: Lucene-style query to filter events (see [Query Syntax](#query-syntax))
- `aggregation_type`: Type of aggregation to perform (see [Aggregation Types](#aggregation-types))
- `aggregation_field`: Field to aggregate on
- `aggregation_count`: Minimum threshold for the aggregation to be considered a match

---

## Use Cases

### 1. Brute Force Detection

Detect multiple failed login attempts (with different error codes) followed by a successful login:

```yaml
name: "Brute Force Login Detection"
type: "elastalert_modules.custom_rule_types.CorrelationRule"
index: windows-logs-*

num_events: 1
timeframe:
  minutes: 15

query_key: user.name

correlated_events:
  - position: 1
    type: aggregation
    query: "resultType:(50097 OR 50140 OR 50126 OR 0)"  # Various failure codes
    aggregation_type: cardinality
    aggregation_field: resultType
    aggregation_count: 3                                # At least 3 different failure types
  - position: 2
    key: resultSignature
    value: SUCCESS

alert: slack
slack_webhook_url: "https://hooks.slack.com/..."
```

### 2. AWS API Sequence Detection

Detect suspicious AWS API call sequences (original use case):

```yaml
name: "Suspicious AWS Instance Manipulation"
type: "elastalert_modules.custom_rule_types.CorrelationRule"
index: cloudtrail-*

num_events: 1
timeframe:
  minutes: 10

query_key: userIdentity.principalId

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

alert: email
email: ["aws-security@example.com"]
```

### 3. Multiple Failed Actions with Count

Detect at least 5 failed authentication attempts followed by a success:

```yaml
name: "Multiple Failed Auth Attempts"
type: "elastalert_modules.custom_rule_types.CorrelationRule"
index: auth-logs-*

num_events: 1
timeframe:
  minutes: 5

query_key: source.ip

correlated_events:
  - position: 1
    type: aggregation
    query: "status:failed"
    aggregation_type: count
    aggregation_field: status      # Not used for count, but required
    aggregation_count: 5            # At least 5 failed attempts
  - position: 2
    key: status
    value: success

alert: pagerduty
pagerduty_service_key: "your-key"
```

---

## Examples

### Example 1: Basic Key-Value Correlation

This example detects when a user stops an EC2 instance, modifies it, and starts it again:

```yaml
name: "EC2 Instance Manipulation Pattern"
type: "elastalert_modules.custom_rule_types.CorrelationRule"
index: cloudtrail-*

num_events: 1
timeframe:
  hours: 1

query_key: userIdentity.arn

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

alert: email
email: ["cloud-ops@example.com"]
```

### Example 2: Aggregation with Cardinality

Detect 4 unique failure types followed by success (your use case):

```yaml
name: "Multiple Unique Failures Before Success"
type: "elastalert_modules.custom_rule_types.CorrelationRule"
index: authentication-*

num_events: 1
timeframe:
  minutes: 10

query_key: user.id

correlated_events:
  - position: 1
    type: aggregation
    query: "resultType:(50097 OR 50140 OR 50126 OR 0)"
    aggregation_type: cardinality
    aggregation_field: resultType
    aggregation_count: 4
  - position: 2
    key: resultSignature
    value: SUCCESS

alert: email
email: ["security@example.com"]

alert_subject: "Alert: User {0} had 4 different failures before success"
alert_subject_args:
  - user.id

alert_text: |
  User: {0}
  Time: {1}
  Multiple unique failure types detected before successful authentication.
  This may indicate a brute force attack or credential stuffing.

alert_text_args:
  - user.id
  - "@timestamp"
```

### Example 3: Mixed Matching Types

Combine aggregation and regular matching for complex patterns:

```yaml
name: "Privilege Escalation Pattern"
type: "elastalert_modules.custom_rule_types.CorrelationRule"
index: security-logs-*

num_events: 1
timeframe:
  minutes: 30

query_key: user.name

correlated_events:
  - position: 1
    type: aggregation
    query: "action:(view OR read)"
    aggregation_type: count
    aggregation_field: action
    aggregation_count: 10                # 10+ reconnaissance actions
  - position: 2
    key: action
    value: privilege_escalation_attempt  # Followed by escalation attempt
  - position: 3
    key: action
    value: admin_action                  # Followed by admin action

alert: slack
slack_webhook_url: "https://hooks.slack.com/..."
```

### Example 4: No Query Key (Global Correlation)

Detect patterns across all users (not grouped by a specific field):

```yaml
name: "System-Wide Attack Pattern"
type: "elastalert_modules.custom_rule_types.CorrelationRule"
index: system-logs-*

num_events: 2  # At least 2 complete sequences
timeframe:
  minutes: 5

# No query_key means all events are correlated together

correlated_events:
  - position: 1
    key: event.type
    value: network_scan
  - position: 2
    key: event.type
    value: exploit_attempt

alert: pagerduty
pagerduty_service_key: "your-key"
```

---

## Aggregation Types

### Cardinality

Counts unique values in the specified field. Useful for detecting diversity in attack patterns.

```yaml
aggregation_type: cardinality
aggregation_field: error.code
aggregation_count: 3  # At least 3 unique error codes
```

**Use cases:**
- Multiple different failure types (brute force with credential rotation)
- Different attack vectors tried
- Various error codes encountered

### Count

Counts the number of events matching the query. Useful for detecting volume-based patterns.

```yaml
aggregation_type: count
aggregation_field: any_field  # Field is required but not used for count
aggregation_count: 10         # At least 10 matching events
```

**Use cases:**
- Multiple failed attempts (same or different types)
- High volume of specific events
- Repeated actions

---

## Query Syntax

The `query` parameter supports Lucene-style syntax:

### Simple Field-Value Match

```yaml
query: "status:failed"
```

### OR Operator

```yaml
query: "resultType:(50097 OR 50140 OR 50126 OR 0)"
```

This matches events where `resultType` equals any of: 50097, 50140, 50126, or 0.

### Field with Single Value

```yaml
query: "action:login"
```

### Currently Supported Syntax

- `field:value` - Simple equality
- `field:(value1 OR value2 OR value3)` - Multiple values with OR

**Note**: The current implementation supports basic queries. For more complex queries (AND, NOT, wildcards, ranges), you may need to extend the `parse_query_and_match` method in `custom_rule_types.py`.

---

## Advanced Examples

### Example: Detecting Account Takeover Pattern

Detect login from new location after multiple failed attempts:

```yaml
name: "Account Takeover Detection"
type: "elastalert_modules.custom_rule_types.CorrelationRule"
index: auth-logs-*

num_events: 1
timeframe:
  minutes: 20

query_key: user.email

correlated_events:
  - position: 1
    type: aggregation
    query: "auth.result:(failure OR denied)"
    aggregation_type: count
    aggregation_field: auth.result
    aggregation_count: 5
  - position: 2
    key: auth.result
    value: success
  - position: 3
    key: geo.country_code
    value: RU  # Or any suspicious location

filter:
  - query:
      bool:
        must_not:
          - term:
              user.type: "service_account"

alert: email
email: ["security-team@example.com"]
```

### Example: Multi-Stage Attack Detection

Detect reconnaissance followed by exploitation:

```yaml
name: "Multi-Stage Attack Pattern"
type: "elastalert_modules.custom_rule_types.CorrelationRule"
index: security-*

num_events: 1
timeframe:
  hours: 2

query_key: source.ip

correlated_events:
  - position: 1
    type: aggregation
    query: "event.category:(network OR web)"
    aggregation_type: cardinality
    aggregation_field: destination.port
    aggregation_count: 10  # Scanned 10+ different ports
  - position: 2
    key: event.category
    value: intrusion_detection
  - position: 3
    key: event.outcome
    value: success

alert: slack
slack_webhook_url: "https://hooks.slack.com/..."
```

### Example: Data Exfiltration Pattern

Detect unusual file access followed by large upload:

```yaml
name: "Potential Data Exfiltration"
type: "elastalert_modules.custom_rule_types.CorrelationRule"
index: file-access-*

num_events: 1
timeframe:
  minutes: 30

query_key: user.id

correlated_events:
  - position: 1
    type: aggregation
    query: "file.type:(sensitive OR confidential OR secret)"
    aggregation_type: count
    aggregation_field: file.path
    aggregation_count: 20  # Accessed 20+ sensitive files
  - position: 2
    key: event.action
    value: file_compress
  - position: 3
    key: network.direction
    value: outbound

alert: pagerduty
pagerduty_service_key: "your-key"
```

---

## How It Works

### Sequence Matching Algorithm

The correlation rule works by:

1. **Collecting Events**: Events within the timeframe are stored in an `EventWindow`
2. **Grouping** (if `query_key` is specified): Events are grouped by the query key value
3. **Position Matching**: For each correlated event position:
   - **Regular matching**: Find indices where field equals value
   - **Aggregation matching**: Find indices where aggregation threshold is met
4. **Sequence Detection**: Find valid sequences where positions increase monotonically
5. **Alert Triggering**: If `num_events` or more complete sequences are found, trigger alert

### Example Sequence Detection

Given events: `[A, B, A, C, B, C]` and correlation: `[A, B, C]`

- Position 1 (A): indices `[0, 2]`
- Position 2 (B): indices `[1, 4]`
- Position 3 (C): indices `[3, 5]`

Valid sequences: `0→1→3` and `2→4→5` = **2 matches**

### Aggregation Indices

For aggregation events, indices represent where the aggregation threshold was met:

Given events with `resultType`: `[50097, 50140, 50097, 50126, SUCCESS]`

For cardinality of 3 on `resultType:(50097 OR 50140 OR 50126)`:
- Index 0: 1 unique value (50097)
- Index 1: 2 unique values (50097, 50140)
- Index 2: 2 unique values (still just 50097, 50140)
- Index 3: 3 unique values (50097, 50140, 50126) ✓ Threshold met

Indices: `[3]` (only index 3 meets the threshold of 3 unique values)

---

## Troubleshooting

### No Alerts Triggered

1. **Check timeframe**: Ensure events occur within the specified timeframe
2. **Verify query_key**: If using query_key, events must have matching values
3. **Check num_events**: Reduce to 1 for testing
4. **Enable debug logging**: Add to ElastAlert2 config:
   ```yaml
   logging:
     level: DEBUG
   ```

### Query Not Matching

1. **Test query syntax**: Verify field names match your index mapping
2. **Check field types**: Ensure field values are in the expected format
3. **Review logs**: Look for `Unrecognized query format` warnings

### Performance Issues

1. **Narrow timeframe**: Use smaller time windows
2. **Add filters**: Use ElastAlert2's `filter` to reduce events processed
3. **Use query_key**: Group events by a specific field to reduce correlation complexity

---

## Extending the Implementation

### Adding New Aggregation Types

To add new aggregation types (e.g., sum, avg, max, min), modify the `get_aggregation_indices` method in `custom_rule_types.py`:

```python
elif agg_type == 'sum':
    total = 0
    for index, event_tuple in enumerate(events):
        event = event_tuple[0]
        if self.parse_query_and_match(event, query):
            field_value = lookup_es_key(event, agg_field)
            if field_value is not None:
                total += float(field_value)
                if total >= agg_count:
                    indices.append(index)
```

### Enhancing Query Parsing

To support more complex queries (AND, NOT, wildcards), extend the `parse_query_and_match` method:

```python
def parse_query_and_match(self, event, query):
    # Add support for AND operator
    if ' AND ' in query:
        conditions = query.split(' AND ')
        return all(self.parse_query_and_match(event, cond.strip()) for cond in conditions)

    # Add support for NOT operator
    if query.startswith('NOT '):
        return not self.parse_query_and_match(event, query[4:])

    # ... existing code ...
```

---

## Contributing

Issues and pull requests are welcome! This is a community-driven enhancement to ElastAlert2.

## License

This code is provided as-is for use with ElastAlert2. Follow ElastAlert2's license terms.

## Credits

- **Original Implementation**: [@briandefiant](https://github.com/briandefiant) - https://github.com/jertel/elastalert2/discussions/854
- **Aggregation Enhancement**: Community contribution
- **ElastAlert2**: https://github.com/jertel/elastalert2

---

## Support

For questions or issues:
1. Check ElastAlert2 documentation: https://elastalert2.readthedocs.io/
2. Review the original discussion: https://github.com/jertel/elastalert2/discussions/854
3. Open an issue in your repository

## Version History

- **v2.0**: Added aggregation support (cardinality, count)
- **v1.0**: Original implementation (key-value matching only)
