# Chapter 22 – Acceptance Testing

## Core Idea
Unit and integration tests verify that your code does what *you* intended. **Acceptance tests** verify that your code does what the *customer* intended. They are written in a language that non-technical stakeholders can read, review, and sign off on.

## The Problem with Developer-Centric Tests
```python
def test_chili_has_correct_ingredients():
    assert make_chili().ingredients == ["Ground Beef", "Chile Blend", "Onion", "Tomatoes", "Pinto Beans"]
```
This test passes — but the customer wanted Texas-style chili (no tomatoes or beans). All the unit tests in the world won't save you from building the wrong thing.

**Verification vs. Validation:**
- **Verification**: are we building the thing *right*? (unit/integration tests)
- **Validation**: are we building the *right* thing? (acceptance tests)

## Behavior-Driven Development (BDD)
BDD formalizes acceptance testing with three practices:
1. Collaborate with stakeholders to define expected behaviors before writing code
2. Express those behaviors in a structured natural language (**Gherkin**)
3. Automate them as executable tests (**behave**)

## The Gherkin Language
Structured English that both humans and machines can read:
```gherkin
Feature: Meal recommendation

  Scenario: Customer requests vegetarian meal under 800 calories
    Given the customer is vegetarian
    And the customer's calorie target is 800
    When the recommendation engine runs
    Then the meal should contain no meat
    And the total calories should be less than 800
```
- **Feature**: the business capability being described
- **Scenario**: a specific example of the feature in action
- **Given**: preconditions / initial state
- **When**: the action being taken
- **Then**: the expected outcome
- **And / But**: additional conditions

Stakeholders can read and validate Gherkin — no code knowledge required.

## Executable Specifications with behave
Map Gherkin steps to Python functions:
```python
from behave import given, when, then

@given("the customer is vegetarian")
def step_set_vegetarian(context):
    context.customer = Customer(dietary_restriction="vegetarian")

@when("the recommendation engine runs")
def step_run_recommendation(context):
    context.meal = recommend_meal(context.customer)

@then("the meal should contain no meat")
def step_verify_no_meat(context):
    assert all(not ingredient.is_meat for ingredient in context.meal.ingredients)
```
Run with:
```bash
behave
```

## Additional behave Features

### Parameterized Steps
```gherkin
Given the customer's calorie target is <calories>

Examples:
  | calories |
  | 800      |
  | 1200     |
```

### Table-Driven Requirements
```gherkin
Given the following menu items:
  | name    | calories | vegetarian |
  | Salad   | 150      | true       |
  | Steak   | 600      | false      |
```

### Step Matching
behave supports regex in step decorators for flexible parameter capture:
```python
@then("the total calories should be less than {target:d}")
def step_calories_under_target(context, target):
    assert context.meal.total_calories < target
```

### Lifecycle Hooks
`before_scenario`, `after_scenario`, `before_feature`, `after_all` in `environment.py` for setup/teardown.

### Tags for Selective Runs
```gherkin
@slow @integration
Scenario: Full order processing pipeline
```
```bash
behave --tags=@integration --tags=~@slow
```

### Report Generation
```bash
behave --format json -o results.json
behave --format html -o report.html
```

## Closing Thoughts
Acceptance tests are the bridge between business requirements and code. By writing them in Gherkin before implementation, you validate the *right* behavior from the start. behave automates them so they stay green as the code evolves — turning stakeholder sign-off into a continuous, automated check.
