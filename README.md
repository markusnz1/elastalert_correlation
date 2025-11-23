# ElastAlert2 Correlation Rule with Aggregation & Field Comparison

A custom ElastAlert2 rule type that detects sequences of correlated events within a timeframe, with support for simple key-value matching, advanced aggregation-based matching, and field comparison between correlated positions.

**Original Implementation**: https://github.com/jertel/elastalert2/discussions/854 by [@briandefiant](https://github.com/briandefiant)

**Enhanced with**:
- Aggregation support for detecting patterns like multiple failed attempts followed by success
- Field comparison support for detecting geo-anomalies, privilege changes, and cross-position validation

---

## Table of Contents

- [Overview](#overview)
- [Repository Structure](#repository-structure)
- [Installation](#installation)
- [Configuration](#configuration)
  - [Basic Configuration](#basic-configuration)
  - [Regular Key-Value Matching](#regular-key-value-matching)
  - [Aggregation-Based Matching](#aggregation-based-matching)
  - [Field Comparison Matching](#field-comparison-matching)
- [Use Cases](#use-cases)
- [Examples](#examples)
- [Aggregation Types](#aggregation-types)
- [Field Comparison Conditions](#field-comparison-conditions)
- [Query Syntax](#query-syntax)
- [Advanced Examples](#advanced-examples)

---

## Overview

The `CorrelationRule` detects sequences of events that occur in a specific order within a defined timeframe. It supports three types of event matching:

1. **Regular Key-Value Matching**: Match events where a specific field equals a specific value
2. **Aggregation-Based Matching**: Match based on aggregations (e.g., cardinality, count) across events matching a query
3. **Field Comparison Matching**: Compare field values between correlated positions to detect changes or anomalies

This is particularly useful for security use cases like:
- Detecting multiple failed login attempts followed by a successful login
- Identifying suspicious sequences of AWS API calls
- Tracking multi-stage attack patterns
- **Detecting impossible travel/geo-anomalies** (e.g., login from different countries)
- **Identifying privilege escalation** (e.g., role changes between events)
- **Spotting credential compromise** (e.g., IP address changes for same user)

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

### Field Comparison Matching

Compare field values between correlated positions to detect changes or anomalies:

```yaml
correlated_events:
  - position: 1
    key: resultType
    value: "50074"
    capture_fields:                                    # Capture fields from this position
      - field: location.countryOrRegion                # Field to capture
        as: failed_auth_country                        # Store as this name
      - field: ipAddress
        as: failed_auth_ip
  - position: 2
    key: resultType
    value: "0"
    compare_fields:                                    # Compare with captured fields
      - field: location.countryOrRegion                # Field to compare
        to: failed_auth_country                        # Compare with captured value
        condition: not_equal                           # Condition (default: not_equal)
```

**Field Comparison Parameters:**

- `capture_fields`: List of fields to capture from matched events at this position
  - `field`: Field name to capture
  - `as`: Name to store the captured value (used in later comparisons)
- `compare_fields`: List of field comparisons to validate
  - `field`: Field name to compare
  - `to`: Name of previously captured value
  - `condition`: Comparison condition (see [Field Comparison Conditions](#field-comparison-conditions))

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

## Field Comparison Conditions

Field comparison allows you to detect when values change or remain the same between correlated positions. This is powerful for detecting anomalies and suspicious behavior patterns.

### Available Conditions

#### `not_equal` (Default)
Values must be **different** between positions.

```yaml
compare_fields:
  - field: location.country
    to: initial_country
    condition: not_equal  # Alert if country changed
```

**Use cases:**
- Impossible travel (country/city changes)
- IP address changes
- User agent switches
- Device fingerprint mismatches

#### `equal`
Values must be the **same** between positions.

```yaml
compare_fields:
  - field: source.ip
    to: initial_ip
    condition: equal  # Alert only if IP stays the same
```

**Use cases:**
- Verify consistency across events
- Ensure same source for multi-step operations
- Validate session continuity

#### `greater_than`
Numeric value must be **greater** than captured value.

```yaml
compare_fields:
  - field: user.privilege_level
    to: initial_privilege
    condition: greater_than  # Privilege escalation
```

**Use cases:**
- Privilege escalation detection
- Data volume increases
- Access level changes
- Severity increases

#### `less_than`
Numeric value must be **less** than captured value.

```yaml
compare_fields:
  - field: authentication.strength
    to: initial_auth_strength
    condition: less_than  # Weaker authentication used
```

**Use cases:**
- Authentication downgrade detection
- Security level decreases
- Monitoring threshold drops

#### `contains`
Value must **contain** the captured value as a substring.

```yaml
compare_fields:
  - field: user_agent
    to: initial_browser
    condition: contains  # Same browser family
```

**Use cases:**
- Partial string matching
- Domain/subdomain validation
- Browser family detection

#### `not_contains`
Value must **not contain** the captured value as a substring.

```yaml
compare_fields:
  - field: destination.domain
    to: trusted_domain
    condition: not_contains  # Accessing untrusted domains
```

**Use cases:**
- Detect access to unexpected resources
- Identify deviation from normal patterns

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

### Example: Phishing Detection with Impossible Travel

Detect when a user has a failed authentication from one country followed by a successful login from a different country (strong indicator of credential compromise):

```yaml
name: "Phishing Detection - Country Mismatch After Failed Auth"
type: "elastalert_modules.custom_rule_types.CorrelationRule"
index: nvsoc_*_azure-*

timeframe:
  hours: 1  # Short timeframe for impossible travel detection

realert:
  hours: 48

filter:
  - query:
      query_string:
        query: 'operationName:"Sign-in activity" AND resultType:(50074 OR 0) AND riskEventTypes:*'

# Group by user to detect same user across different countries
query_key:
  - signInIdentifier

num_events: 1
correlated_events:
  # Position 1: Failed authentication attempt (user doesn't exist or error)
  - position: 1
    key: resultType
    value: "50074"
    capture_fields:
      - field: location.countryOrRegion  # Capture country from failed attempt
        as: failed_auth_country
      - field: ipAddress                 # Also capture IP for context
        as: failed_auth_ip

  # Position 2: Successful login from a DIFFERENT country (strong phishing indicator)
  - position: 2
    key: resultType
    value: "0"
    compare_fields:
      - field: location.countryOrRegion  # Compare with captured country
        to: failed_auth_country
        condition: not_equal              # Alert only if country is different

alert:
  - email
email: ["security@example.com"]

alert_text: |
  Potential Phishing Detected - Impossible Travel

  User: {signInIdentifier}

  Sequence:
  1. Failed auth from country: {failed_auth_country} (IP: {failed_auth_ip})
  2. Successful login from different country: {location.countryOrRegion}

  Timeframe: Within 1 hour

  This pattern suggests credential compromise or phishing attack.
```

**Why this works:**
- Captures the country from the failed authentication attempt
- Only alerts if the successful login is from a **different country**
- Uses `query_key` to track per-user sequences
- Short 1-hour timeframe for true impossible travel scenarios

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

### Example: Privilege Escalation Detection with Role Comparison

Detect when a user's role or privilege level changes between events:

```yaml
name: "Privilege Escalation Detection"
type: "elastalert_modules.custom_rule_types.CorrelationRule"
index: audit-logs-*

timeframe:
  minutes: 30

query_key: user.id

num_events: 1
correlated_events:
  - position: 1
    key: event.action
    value: login
    capture_fields:
      - field: user.role
        as: initial_role
      - field: user.privilege_level
        as: initial_privilege

  - position: 2
    key: event.action
    value: access_sensitive_resource
    compare_fields:
      - field: user.role
        to: initial_role
        condition: not_equal  # Role changed
      - field: user.privilege_level
        to: initial_privilege
        condition: greater_than  # Privilege increased

alert: slack
slack_webhook_url: "https://hooks.slack.com/..."

alert_text: |
  Privilege Escalation Detected

  User: {user.id}
  Initial Role: {initial_role}
  Current Role: {user.role}
  Initial Privilege: {initial_privilege}
  Current Privilege: {user.privilege_level}

  This user's privileges increased between login and sensitive resource access.
```

### Example: IP Address Change Detection (Session Hijacking)

Detect when the same session/token is used from different IP addresses:

```yaml
name: "Potential Session Hijacking"
type: "elastalert_modules.custom_rule_types.CorrelationRule"
index: web-access-*

timeframe:
  minutes: 10

query_key: session.token

num_events: 1
correlated_events:
  - position: 1
    key: event.action
    value: api_request
    capture_fields:
      - field: source.ip
        as: original_ip
      - field: user_agent.original
        as: original_user_agent

  - position: 2
    key: event.action
    value: api_request
    compare_fields:
      - field: source.ip
        to: original_ip
        condition: not_equal  # Different IP address
      - field: user_agent.original
        to: original_user_agent
        condition: not_equal  # Different user agent

alert: pagerduty
pagerduty_service_key: "your-key"

alert_text: |
  Potential Session Hijacking Detected

  Session Token: {session.token}
  User: {user.name}

  Original Request:
  - IP: {original_ip}
  - User Agent: {original_user_agent}

  Suspicious Request:
  - IP: {source.ip}
  - User Agent: {user_agent.original}

  Same session token used from different IP and browser within {timeframe}.
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
   - **Field comparison matching**:
     - Capture field values at earlier positions
     - Compare current event's fields with captured values
     - Only include indices where comparisons pass
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

## Combining Features

You can combine all three matching types (key-value, aggregation, and field comparison) in a single rule for sophisticated detection:

```yaml
name: "Advanced Threat Detection - Combined Features"
type: "elastalert_modules.custom_rule_types.CorrelationRule"
index: security-*

timeframe:
  hours: 2

query_key: user.id

num_events: 1
correlated_events:
  # Position 1: Multiple failed attempts (aggregation)
  - position: 1
    type: aggregation
    query: "auth.result:(failure OR denied)"
    aggregation_type: cardinality
    aggregation_field: auth.method
    aggregation_count: 3  # At least 3 different auth methods tried
    capture_fields:
      - field: source.country
        as: initial_country
      - field: source.ip
        as: initial_ip

  # Position 2: Successful auth (key-value matching)
  - position: 2
    key: auth.result
    value: success
    capture_fields:
      - field: user.privilege_level
        as: login_privilege

  # Position 3: High-value action (key-value + field comparison)
  - position: 3
    key: event.category
    value: admin_action
    compare_fields:
      - field: source.country
        to: initial_country
        condition: not_equal  # Different country than initial attempts
      - field: user.privilege_level
        to: login_privilege
        condition: greater_than  # Privilege escalated since login

alert: pagerduty
pagerduty_service_key: "your-key"

alert_text: |
  High-Confidence Threat Detected

  User: {user.id}

  Attack Pattern:
  1. Multiple auth methods tried (3+) from {initial_country}
  2. Successful login with privilege level {login_privilege}
  3. Admin action performed from different country with elevated privileges

  This pattern indicates a sophisticated attack with:
  - Brute force/credential stuffing
  - Successful compromise
  - Privilege escalation
  - Impossible travel
```

This example demonstrates:
- **Aggregation** at position 1 (multiple auth methods)
- **Field capture** at positions 1 and 2 (country, IP, privilege)
- **Key-value matching** at all positions
- **Field comparison** at position 3 (country change + privilege increase)

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

### Field Comparison Not Working

1. **Verify field names**: Ensure field names in `capture_fields` and `compare_fields` match your Elasticsearch schema exactly
2. **Check field values**: Fields must be non-null to be captured and compared
3. **Test without comparison**: First verify the basic correlation works, then add field comparison
4. **Check captured values**: Enable debug logging to see what values are being captured:
   ```yaml
   logging:
     level: DEBUG
   ```
5. **Multiple captures**: If capturing the same field name at different indices, the implementation will use the most recently captured value

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

- **v3.0**: Added field comparison support
  - `capture_fields`: Capture field values from any position
  - `compare_fields`: Compare fields between positions
  - Six comparison conditions: `equal`, `not_equal`, `greater_than`, `less_than`, `contains`, `not_contains`
  - Use cases: Impossible travel, privilege escalation, session hijacking, IP changes
- **v2.0**: Added aggregation support (cardinality, count)
- **v1.0**: Original implementation (key-value matching only)
