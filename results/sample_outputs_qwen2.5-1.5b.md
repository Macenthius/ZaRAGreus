# Sample outputs (qwen2.5:1.5b, hybrid retrieval, top_k=4)

Generated automatically by `scripts/evaluate.py` from a real run. Examples are chosen by rule: highest key-fact coverage, lowest coverage, refusals, and any refusal failures.

## q01 - Good answer

**Question:** What are the three rules of ownership in Rust?

**Best dense similarity:** 0.8474  |  **Refused:** False  |  **Key facts found:** ['owner', 'one owner', 'out of scope', 'dropped'] of ['owner', 'one owner', 'out of scope', 'dropped']  |  **Latency:** retrieve 196.2 ms, generate 11545.9 ms

**Answer:**

> Each value in Rust has an _owner_. There can only be one owner at a time. When the owner goes out of scope, the value will be dropped.

**Retrieved sources:**

1. `ch04-01-what-is-ownership::005::43e548` - Understanding Ownership > What Is Ownership? > Ownership Rules (dense=0.8474, bm25=14.495, fused=0.03279)
2. `ch04-01-what-is-ownership::000::7a9bba` - Understanding Ownership > What Is Ownership? (dense=0.846, bm25=13.644, fused=0.03226)
3. `ch04-01-what-is-ownership::008::a85218` - Understanding Ownership > What Is Ownership? > The String Type (dense=0.7606, bm25=10.935, fused=0.03008)
4. `ch04-01-what-is-ownership::022::fed145` - Understanding Ownership > What Is Ownership? > Ownership and Functions (dense=0.7369, bm25=9.671, fused=0.02744)

## q05 - Good answer

**Question:** How does Rust prevent dangling references?

**Best dense similarity:** 0.8917  |  **Refused:** False  |  **Key facts found:** ['dangling', 'compiler', 'out of scope'] of ['dangling', 'compiler', 'out of scope']  |  **Latency:** retrieve 48.8 ms, generate 3993.2 ms

**Answer:**

> Rust prevents dangling references by ensuring that references will never be dangling references. If you have a reference to some data, the compiler will ensure that the data will not go out of scope before the reference to the data does. This is achieved through the use of lifetimes, which help prevent references from pointing to data that has already been dropped.

**Retrieved sources:**

1. `ch04-02-references-and-borrowing::007::8ff69c` - Understanding Ownership > References and Borrowing > Dangling References (dense=0.8917, bm25=13.024, fused=0.03252)
2. `ch10-03-lifetime-syntax::001::450f1f` - Generic Types, Traits, and Lifetimes > Validating References with Lifetimes > Dangling References (dense=0.8576, bm25=15.599, fused=0.03252)
3. `ch04-02-references-and-borrowing::008::7ab6b9` - Understanding Ownership > References and Borrowing > Dangling References (dense=0.8368, bm25=9.737, fused=0.03058)
4. `ch20-01-unsafe-rust::003::ca486b` - Advanced Features > Unsafe Rust > Dereferencing a Raw Pointer (dense=0.8177, bm25=12.461, fused=0.03055)

## q09 - Good answer

**Question:** Why does Rust use Option<T> instead of null?

**Best dense similarity:** 0.8463  |  **Refused:** False  |  **Key facts found:** ['some', 'none', 'null'] of ['some', 'none', 'null']  |  **Latency:** retrieve 75.9 ms, generate 4867.6 ms

**Answer:**

> Rust uses `Option<T>` instead of null because it provides a way to encode the concept of a value being present or absent, which is useful for handling scenarios where a value might not be available. This enum, `Option<T>`, is defined by the standard library as:
> 
> ```rust
> enum Option<T> {
>     None,
>     Some(T),
> }
> ```
> 
> By using `Option<T>`, Rust ensures that the compiler can check whether a value is present or absent, preventing common errors and making the code safer. This approach limits the pervasiveness of null values, making the language safer and more reliable.

**Retrieved sources:**

1. `ch06-01-defining-an-enum::012::6a4e09` - Enums and Pattern Matching > Defining an Enum > The Option Enum (dense=0.8463, bm25=26.829, fused=0.03279)
2. `ch06-01-defining-an-enum::010::60570e` - Enums and Pattern Matching > Defining an Enum > The Option Enum (dense=0.8205, bm25=23.338, fused=0.032)
3. `ch06-01-defining-an-enum::008::8a644d` - Enums and Pattern Matching > Defining an Enum > The Option Enum (dense=0.8045, bm25=22.132, fused=0.03126)
4. `ch06-01-defining-an-enum::007::480e35` - Enums and Pattern Matching > Defining an Enum > The Option Enum (dense=0.8242, bm25=15.519, fused=0.03083)

## q11 - Good answer

**Question:** When should I use if let instead of match?

**Best dense similarity:** 0.8101  |  **Refused:** False  |  **Key facts found:** ['if let', 'one pattern', 'less'] of ['if let', 'one pattern', 'less']  |  **Latency:** retrieve 94.3 ms, generate 2988.9 ms

**Answer:**

> When you want to combine `if` and `let` into a less verbose way to handle values that match one pattern while ignoring the rest, use `if let`. This is useful when you need to perform some computation when a value is present and return a default value otherwise.

**Retrieved sources:**

1. `ch06-03-if-let::002::194775` - Enums and Pattern Matching > Concise Control Flow with if let and let...else (dense=0.7737, bm25=9.451, fused=0.03128)
2. `ch06-03-if-let::000::bbdeb4` - Enums and Pattern Matching > Concise Control Flow with if let and let...else (dense=0.8061, bm25=8.017, fused=0.03062)
3. `ch06-03-if-let::003::070b41` - Enums and Pattern Matching > Staying on the “Happy Path” with let...else (dense=0.7582, bm25=8.287, fused=0.02963)
4. `ch19-02-refutability::003::c7e188` - Patterns and Matching > Refutability: Whether a Pattern Might Fail to Match (dense=0.74, bm25=7.529, fused=0.0278)

## q04 - Weak / failure case

**Question:** What are the rules of references in Rust?

**Best dense similarity:** 0.817  |  **Refused:** False  |  **Key facts found:** [] of ['one mutable reference', 'immutable references', 'valid']  |  **Latency:** retrieve 71.1 ms, generate 4263.7 ms

**Answer:**

> The rules of references in Rust are:
> 
> 1. The compiler assigns a lifetime parameter to each parameter that's a reference.
> 2. If there is exactly one input lifetime parameter, that lifetime is assigned to all output lifetime parameters.
> 3. If there are multiple input lifetime parameters, but one of them is `&self` or `&mut self` because this is a method, the lifetime of `self` is assigned to all output lifetime parameters.

**Retrieved sources:**

1. `ch10-03-lifetime-syntax::019::2335fd` - Generic Types, Traits, and Lifetimes > Validating References with Lifetimes > Lifetime Elision (dense=0.7983, bm25=12.028, fused=0.03151)
2. `ch15-05-interior-mutability::001::6c3676` - Smart Pointers > RefCell<T> and the Interior Mutability Pattern > Enforcing Borrowing Rules at Runtime (dense=0.7952, bm25=13.04, fused=0.03089)
3. `ch10-03-lifetime-syntax::020::d5dfc4` - Generic Types, Traits, and Lifetimes > Validating References with Lifetimes > Lifetime Elision (dense=0.7767, bm25=9.666, fused=0.02743)
4. `ch15-00-smart-pointers::001::64dcc0` - Smart Pointers (dense=0.7792, bm25=7.765, fused=0.02597)

## q08 - Weak / failure case

**Question:** What is the difference between a method and an associated function?

**Best dense similarity:** 0.7528  |  **Refused:** False  |  **Key facts found:** ['self'] of ['self', '::', 'new']  |  **Latency:** retrieve 53.5 ms, generate 3752.9 ms

**Answer:**

> A method is a function that takes a `self` parameter, while an associated function does not have a `self` parameter. When there are multiple types or traits that define non-method functions with the same function name, Rust doesn't always know which type you mean unless you use fully qualified syntax.

**Retrieved sources:**

1. `ch20-02-advanced-traits::010::f38bce` - Advanced Features > Advanced Traits > Disambiguating Between Identically Named Methods (dense=0.6848, bm25=10.299, fused=0.03175)
2. `ch20-02-advanced-traits::002::9be2dc` - Advanced Features > Advanced Traits > Defining Traits with Associated Types (dense=0.6539, bm25=14.217, fused=0.03048)
3. `ch20-02-advanced-traits::003::795e8e` - Advanced Features > Advanced Traits > Defining Traits with Associated Types (dense=0.6621, bm25=7.156, fused=0.02899)
4. `ch20-05-macros::001::c53a22` - Advanced Features > Macros > The Difference Between Macros and Functions (dense=0.6436, bm25=8.402, fused=0.02854)

## u01 - Correct refusal

**Question:** What is the capital of France?

**Best dense similarity:** 0.4569  |  **Refused:** True  |  **Key facts found:** [] of []  |  **Latency:** retrieve 51.0 ms, generate 0.0 ms

**Answer:**

> I couldn't find this in the Rust Book.

**Retrieved sources:**

1. `ch08-02-strings::010::aa5af6` - Common Collections > Storing UTF-8 Encoded Text with Strings > Indexing into Strings > Internal Representation (dense=0.4189, bm25=5.975, fused=0.03041)
2. `appendix-06-translation::000::eaf2be` - F - Translations of the Book > Appendix F: Translations of the Book (dense=0.4569, bm25=None, fused=0.01639)
3. `ch12-05-working-with-environment-variables::002::97afd1` - An I/O Project: Building a Command Line Program > Working with Environment Variables > Writing a Failing Test for Case-Insensitive Search (dense=None, bm25=6.576, fused=0.01639)
4. `ch06-02-match::004::779504` - Enums and Pattern Matching > The match Control Flow Construct > Patterns That Bind to Values (dense=0.4361, bm25=None, fused=0.01613)

## u02 - Correct refusal

**Question:** How do I write a list comprehension in Python?

**Best dense similarity:** 0.6854  |  **Refused:** True  |  **Key facts found:** [] of []  |  **Latency:** retrieve 48.5 ms, generate 0.0 ms

**Answer:**

> I couldn't find this in the Rust Book.

**Retrieved sources:**

1. `ch01-02-hello-world::006::871c52` - Getting Started > Hello, World! > Compilation and Execution (dense=None, bm25=11.42, fused=0.01639)
2. `ch04-03-slices::002::d36472` - Understanding Ownership > The Slice Type (dense=0.6854, bm25=None, fused=0.01639)
3. `ch13-01-closures::009::8fbff1` - Functional Language Features: Iterators and Closures > Closures > Capturing References or Moving Ownership (dense=None, bm25=8.118, fused=0.01613)
4. `ch19-01-all-the-places-for-patterns::008::a95307` - Patterns and Matching > All the Places Patterns Can Be Used > for Loops (dense=0.6622, bm25=None, fused=0.01613)

## u10 - Missed refusal (failure)

**Question:** How do I declare a goroutine and a WaitGroup in Go?

**Best dense similarity:** 0.7076  |  **Refused:** False  |  **Key facts found:** [] of []  |  **Latency:** retrieve 73.4 ms, generate 3349.4 ms

**Answer:**

> To declare a goroutine and a WaitGroup in Go, you would use the `go` keyword to create a goroutine and the `sync.WaitGroup` type to create a WaitGroup. For example:
> 
> ```rust,noplayground,test_harness
> go func() {
>     // Your goroutine code here
> }
> 
> var wg sync.WaitGroup
> wg.Add(1)
> go func() {
>     wg.Done()
> }
> ```

**Retrieved sources:**

1. `ch07-04-bringing-paths-into-scope-with-the-use-keyword::002::343532` - Packages, Crates, and Modules > Bringing Paths into Scope with the use Keyword > Creating Idiomatic use Paths (dense=0.7076, bm25=None, fused=0.01639)
2. `ch20-01-unsafe-rust::020::9e2d3f` - Advanced Features > Unsafe Rust > Implementing an Unsafe Trait (dense=None, bm25=7.819, fused=0.01639)
3. `ch09-02-recoverable-errors-with-result::012::6186f7` - Error Handling > Recoverable Errors with Result > Propagating Errors > The ? Operator Shortcut (dense=None, bm25=6.407, fused=0.01613)
4. `ch17-03-more-futures::002::f21d97` - Fundamentals of Asynchronous Programming: Async, Await, Futures, and Streams > Yielding Control to the Runtime (dense=0.6977, bm25=None, fused=0.01613)
