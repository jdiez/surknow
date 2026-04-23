Review recent changes for design principle adherence. No arguments needed.

Check every changed or new `.py` file against the project's Design Principles (see CLAUDE.md):

### 1. Paradigm fit
- Classes with only one method or no state → should be a function
- Pure data transformation wrapped in a class → should be functional
- Stateful logic scattered in loose functions → should be a class
- Flag: "This class/function would be simpler as [alternative]"

### 2. Design pattern usage
- Unnecessary patterns (Singleton where module-level instance works, Factory for a static mapping, ABC with one implementor)
- Missing patterns (3+ `if/elif` switching on type → Strategy or singledispatch; repeated object construction logic → Factory/Builder)
- Deep inheritance where composition or Protocol would be simpler
- Flag: "Pattern X is [unnecessary/missing] here because [reason]"

### 3. Async and concurrency
- `async def` on functions that do no I/O → remove async
- Blocking calls (`requests`, `time.sleep`, file I/O) inside async functions without `asyncio.to_thread()` → fix
- Threading used for CPU-bound work → should be multiprocessing
- Concurrency added without measurable need → simplify to sync
- Shared mutable state across threads/processes without synchronization → fix
- Flag: "Concurrency [missing/misapplied] here because [reason]"

### 4. Error handling
- Bare `except:` or `except Exception:` catching too broadly → narrow the catch
- Functions returning `None` to signal error instead of raising → raise specific exception
- Redundant validation deep inside trusted internal code → remove
- Missing validation at system boundaries (user input, API responses) → add
- Flag: "Error handling [too broad/missing/redundant] here because [reason]"

For each finding, explain the principle violated and provide the specific fix. Then implement the fixes and verify with `make check && make test`.
