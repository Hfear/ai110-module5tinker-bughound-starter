# BugHound Mini Model Card (Reflection)

---

## 1) What is this system?

**Name:** BugHound  
**Purpose:** Analyze a Python snippet, propose a fix, and run reliability checks before suggesting whether the fix should be auto-applied.

**Intended users:** Students learning agentic workflows and AI reliability concepts.

---

## 2) How does it work?

BugHound runs a 5 step agentic loop: plan, analyze, act, test, and reflect.

first it plans a quick scan and fix workflow. then it analyzes the code -- in 
heuristic mode it scans for 3 patterns: print statements, bare `except:` blocks, 
and TODO comments. in Gemini mode it sends the code to the LLM and asks for a 
JSON array of issues. if the LLM returns something that cant be parsed, it falls 
back to heuristics.

then it proposes a fix. in heuristic mode it uses regex rewrites -- bare excepts 
become `except Exception as e:` and print statements become `logging.info(`. 
in Gemini mode the LLM rewrites the code directly, attempting minimal behavior 
preserving changes. if the LLM returns empty output it falls back to the 
heuristic fixer.

then it assesses risk by starting at a score of 100 and subtracting points for 
each issue severity and structural change detected. finally it reflects -- if 
the score is 75 or above it approves auto-fix, otherwise it recommends human review.

---

## 3) Inputs and outputs

**Inputs:**

- What kind of code snippets did you try?
  A short python function called `compute(x, y)` with a print statement, a bare except, and a TODO comment.

- What was the "shape" of the input (short scripts, functions, try/except blocks, etc.)?
  About 7 lines, a single function with a try/except block.

**Outputs:**

- What types of issues were detected?
  Both modes caught the print statement, bare except, and TODO comment. Gemini also caught that returning `0` for any error is ambiguous because if `0` is a valid result the caller cant tell if it worked or not.

- What kinds of fixes were proposed?
  Heuristic used regex to replace print with logging and bare except with `except Exception as e:`. Gemini was more precise, it used `except ZeroDivisionError:` and changed `return 0` to `return None`.

- What did the risk report show?
  Risk was HIGH in both modes and auto fix was blocked.

---

## 4) Reliability and safety rules

**Rule 1: Return statements may have been removed**
- What does the rule check?
  if the original code has a `return` statement but the fixed code doesnt, it subtracts 30 from the score.

- Why might that check matter for safety or correctness?
  removing a return statement can completely change what a function does. the caller might get `None` back when it expected a value, which can silently break other parts of the code.

- What is a false positive this rule could cause?
  if the fix rewrites the function in a way that still returns a value but uses different syntax, the rule might still flag it even though nothing is wrong.

- What is a false negative this rule could miss?
  if the return value is changed but the keyword `return` is still there, like `return 0` becoming `return None`, this rule wont catch it. thats why the return type change rule was added.

**Rule 2: Return value type may have changed**
- What does the rule check?
  if the original code has `return 0` and the fixed code has `return None`, it subtracts 20 from the score and flags it for human review.

- Why might that check matter for safety or correctness?
  changing a return type can silently break calling code. if a caller checks `if result < 10` and the function now returns `None`, it will crash.

- What is a false positive this rule could cause?
  it only checks for the specific pattern `return 0` to `return None`, so it could miss other type changes like `return ""` to `return None`.

- What is a false negative this rule could miss?
  any return type change that doesnt match exactly `return 0` to `return None` would not be caught, like changing `return False` to `return None`.

---

## 5) Observed failure modes

1. **BugHound missed an issue it should have caught**
   in heuristic mode the MockClient returns `# MockClient: no rewrite available 
   in offline mode.` as the fix, but the risk assessor still runs against it and 
   flags things like "return statements may have been removed" and "fixed code is 
   much shorter than original" even though there was no real fix at all. the risk 
   report was meaningless because it was scoring a stub comment not actual code.

2. **BugHound suggested a fix that felt risky**
   Gemini changed `return 0` to `return None` in `compute(x, y)` without flagging 
   it as a potentially breaking change. if calling code does something like 
   `if result < 10` it would crash silently because you cant compare `None` to a 
   number. the original risk report didnt catch this at all, which is why the 
   return type change guardrail was added.

---

## 6) Heuristic vs Gemini comparison

- What did Gemini detect that heuristics did not?
  Gemini caught that returning `0` for any error is ambiguous because if `0` is 
  a valid result the caller cant tell if the function worked or failed. heuristics 
  missed this completely because no regex can catch that kind of reasoning.

- What did heuristics catch consistently?
  heuristics reliably caught the print statement, bare except, and TODO comment 
  every single run because they are simple pattern matches.

- How did the proposed fixes differ?
  heuristics replaced print with `logging.info(` and bare except with 
  `except Exception as e:`. Gemini was more precise, it used `except ZeroDivisionError:` 
  specifically because that was the actual exception that made sense for the code. 
  Gemini also removed the TODO and changed `return 0` to `return None`.

- Did the risk scorer agree with your intuition?
  not always. in heuristic mode the risk report scored a stub comment as if it 
  were real code. and Gemini changing the return type didnt get flagged until 
  the new guardrail was added. the scorer felt overly mechanical and missed the 
  semantic meaning of some changes.

---

## 7) Human-in-the-loop decision

- What trigger would you add?
  if the fix changes a return value type, like `return 0` to `return None`, 
  block auto-fix and require human review.

- Where would you implement it (risk_assessor vs agent workflow vs UI)?
  in `risk_assessor.py` as a guardrail rule, because thats where all the other 
  safety checks live and it keeps the logic in one place.

- What message should the tool show the user?
  "Return value type may have changed. Verify calling code before applying this fix."

---

## 8) Improvement idea

add a rule that detects any return type change, not just `return 0` to `return None`. 
right now the guardrail only catches that one specific pattern so it would miss 
things like `return False` to `return None` or `return ""` to `return None`. 
a more general check would compare the return values in the original and fixed code 
and flag any time the type changes. this would make BugHound more reliable without 
adding much complexity.