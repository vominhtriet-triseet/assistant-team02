# AI Service Interface

## Function Signature

``` python
def process_request(user_input: str) -> dict:
    ...
```

## Inputs

-   `user_input`: non-empty natural-language request from the user.

## Outputs

Returns a dictionary containing: - `tasks`: extracted tasks, or an empty
list. - `priorities`: suggested priorities. - `schedule`: a feasible
schedule, or `None` if unavailable. - `message`: a short explanation or
clarification.

## Errors

-   `ValueError`: input is empty or invalid.
-   `RuntimeError`: request processing fails unexpectedly.

## Fallback

If AI processing is unavailable or the request cannot be interpreted,
return a safe response with empty `tasks` and `priorities`,
`schedule: None`, and a message asking the user to clarify. Do not call
an LLM yet; use a placeholder or rule-based implementation.
