# Sample outputs (qwen2.5:0.5b, hybrid retrieval, top_k=4)

Generated automatically by `scripts/evaluate.py` from a real run. Examples are chosen by rule: highest key-fact coverage, lowest coverage, refusals, and any refusal failures.

## q01 - Good answer

**Question:** What are the three rules of ownership in Rust?

**Best dense similarity:** 0.8474  |  **Refused:** False  |  **Key facts found:** ['owner', 'one owner', 'out of scope', 'dropped'] of ['owner', 'one owner', 'out of scope', 'dropped']  |  **Latency:** retrieve 35.8 ms, generate 2463.3 ms

**Answer:**

> - Each value in Rust has an _owner_.
> - There can only be one owner at a time.
> - When the owner goes out of scope, the value will be dropped.

**Retrieved sources:**

1. `ch04-01-what-is-ownership::005::43e548` - Understanding Ownership > What Is Ownership? > Ownership Rules (dense=0.8474, bm25=14.495, fused=0.03279)
2. `ch04-01-what-is-ownership::000::7a9bba` - Understanding Ownership > What Is Ownership? (dense=0.846, bm25=13.644, fused=0.03226)
3. `ch04-01-what-is-ownership::008::a85218` - Understanding Ownership > What Is Ownership? > The String Type (dense=0.7606, bm25=10.935, fused=0.03008)
4. `ch04-01-what-is-ownership::022::fed145` - Understanding Ownership > What Is Ownership? > Ownership and Functions (dense=0.7369, bm25=9.671, fused=0.02744)

## q13 - Good answer

**Question:** Are struct fields public when the struct is marked pub?

**Best dense similarity:** 0.8321  |  **Refused:** False  |  **Key facts found:** ['pub', 'private', 'field'] of ['pub', 'private', 'field']  |  **Latency:** retrieve 133.4 ms, generate 3357.7 ms

**Answer:**

> We can make each field public or not on a case-by-case basis. In Listing 7-9, we’ve defined a public `back_of_house::Breakfast` struct with a public `toast` field but a private `seasonal_fruit` field. This models the case in a restaurant where the customer can pick the type of bread that comes with a meal, but the chef decides which fruit accompanies the meal based on what’s in season and in stock. The available fruit changes quickly, so customers can’t choose the fruit or even see which fruit they’ll get.

**Retrieved sources:**

1. `ch07-03-paths-for-referring-to-an-item-in-the-module-tree::012::d2074c` - Packages, Crates, and Modules > Paths for Referring to an Item in the Module Tree > Making Structs and Enums Public (dense=0.8321, bm25=21.046, fused=0.03279)
2. `ch07-03-paths-for-referring-to-an-item-in-the-module-tree::014::834818` - Packages, Crates, and Modules > Paths for Referring to an Item in the Module Tree > Making Structs and Enums Public (dense=0.8207, bm25=18.998, fused=0.03175)
3. `ch07-03-paths-for-referring-to-an-item-in-the-module-tree::013::451dc0` - Packages, Crates, and Modules > Paths for Referring to an Item in the Module Tree > Making Structs and Enums Public (dense=0.7818, bm25=19.399, fused=0.03175)
4. `ch05-03-method-syntax::004::8a1880` - Using Structs to Structure Related Data > Methods > Method Syntax (dense=0.7344, bm25=16.155, fused=0.02854)

## q16 - Good answer

**Question:** How do I insert a value into a HashMap only if the key has no value?

**Best dense similarity:** 0.8181  |  **Refused:** False  |  **Key facts found:** ['entry', 'or_insert'] of ['entry', 'or_insert']  |  **Latency:** retrieve 109.8 ms, generate 3375.3 ms

**Answer:**

> To insert a value into a HashMap only if the key has no value, you can use the `or_insert` method on the `Entry` enum. This method returns a mutable reference to the value for the corresponding `Entry` key if that key exists, and if not, it inserts the parameter as the new value for this key and returns a mutable reference to the new value. This technique is much cleaner than writing the logic ourselves and, in addition, plays more nicely with the borrow checker.

**Retrieved sources:**

1. `ch08-03-hash-maps::006::926d60` - Common Collections > Storing Keys with Associated Values in Hash Maps > Updating a Hash Map > Adding a Key and Value Only If a Key Isn’t Present (dense=0.8181, bm25=25.555, fused=0.03252)
2. `ch08-03-hash-maps::005::466715` - Common Collections > Storing Keys with Associated Values in Hash Maps > Updating a Hash Map > Overwriting a Value (dense=0.7735, bm25=28.255, fused=0.03227)
3. `ch08-03-hash-maps::007::f9ac55` - Common Collections > Storing Keys with Associated Values in Hash Maps > Updating a Hash Map > Adding a Key and Value Only If a Key Isn’t Present (dense=0.7992, bm25=15.491, fused=0.03151)
4. `ch08-03-hash-maps::002::d1b3f4` - Common Collections > Storing Keys with Associated Values in Hash Maps > Accessing Values in a Hash Map (dense=0.7401, bm25=23.743, fused=0.03126)

## q19 - Good answer

**Question:** How do I specify a trait bound on a generic function?

**Best dense similarity:** 0.8445  |  **Refused:** False  |  **Key facts found:** ['trait bound', '<t:', 'where'] of ['trait bound', '<t:', 'where']  |  **Latency:** retrieve 75.8 ms, generate 3403.7 ms

**Answer:**

> To specify a trait bound on a generic function, you can use the `where` clause after the function signature. For example, to specify that a generic function `notify` should use `Display` and `Summary` as trait bounds, you can write:
> 
> ```rust,ignore
> pub fn notify<T: Summary + Display>(item: &T) {
>     println!("Breaking news! {}", item.summarize());
> }
> ```
> 
> This specifies that `T` must implement both `Summary` and `Display`, and that `T` must also implement `Summary + Display`.

**Retrieved sources:**

1. `ch10-02-traits::011::98674b` - Generic Types, Traits, and Lifetimes > Defining Shared Behavior with Traits > Using Traits as Parameters > Multiple Trait Bounds with the + Syntax (dense=0.8089, bm25=14.984, fused=0.03178)
2. `ch20-03-advanced-types::011::da4b0c` - Advanced Features > Advanced Types > Dynamically Sized Types and the Sized Trait (dense=0.8302, bm25=12.899, fused=0.03175)
3. `ch10-02-traits::010::91d196` - Generic Types, Traits, and Lifetimes > Defining Shared Behavior with Traits > Using Traits as Parameters > Trait Bound Syntax (dense=0.8142, bm25=12.724, fused=0.03102)
4. `ch10-02-traits::012::69d005` - Generic Types, Traits, and Lifetimes > Defining Shared Behavior with Traits > Using Traits as Parameters > Clearer Trait Bounds with where Clauses (dense=0.8445, bm25=11.727, fused=0.03089)

## q04 - Weak / failure case

**Question:** What are the rules of references in Rust?

**Best dense similarity:** 0.817  |  **Refused:** False  |  **Key facts found:** [] of ['one mutable reference', 'immutable references', 'valid']  |  **Latency:** retrieve 140.7 ms, generate 2515.3 ms

**Answer:**

> The rules of references in Rust are called the `Lifetime Elision Rules`. These rules are a set of particular cases that the compiler will consider, and if your code fits these cases, you don't need to write the lifetimes explicitly.

**Retrieved sources:**

1. `ch10-03-lifetime-syntax::019::2335fd` - Generic Types, Traits, and Lifetimes > Validating References with Lifetimes > Lifetime Elision (dense=0.7983, bm25=12.028, fused=0.03151)
2. `ch15-05-interior-mutability::001::6c3676` - Smart Pointers > RefCell<T> and the Interior Mutability Pattern > Enforcing Borrowing Rules at Runtime (dense=0.7952, bm25=13.04, fused=0.03089)
3. `ch10-03-lifetime-syntax::020::d5dfc4` - Generic Types, Traits, and Lifetimes > Validating References with Lifetimes > Lifetime Elision (dense=0.7767, bm25=9.666, fused=0.02743)
4. `ch15-00-smart-pointers::001::64dcc0` - Smart Pointers (dense=0.7792, bm25=7.765, fused=0.02597)

## q08 - Weak / failure case

**Question:** What is the difference between a method and an associated function?

**Best dense similarity:** 0.7528  |  **Refused:** False  |  **Key facts found:** [] of ['self', '::', 'new']  |  **Latency:** retrieve 19.0 ms, generate 2545.0 ms

**Answer:**

> A method is a function that takes a parameter and returns a value. An associated function is a function that is not a method and is associated with a type.

**Retrieved sources:**

1. `ch20-02-advanced-traits::010::f38bce` - Advanced Features > Advanced Traits > Disambiguating Between Identically Named Methods (dense=0.6848, bm25=10.299, fused=0.03175)
2. `ch20-02-advanced-traits::002::9be2dc` - Advanced Features > Advanced Traits > Defining Traits with Associated Types (dense=0.6539, bm25=14.217, fused=0.03048)
3. `ch20-02-advanced-traits::003::795e8e` - Advanced Features > Advanced Traits > Defining Traits with Associated Types (dense=0.6621, bm25=7.156, fused=0.02899)
4. `ch20-05-macros::001::c53a22` - Advanced Features > Macros > The Difference Between Macros and Functions (dense=0.6436, bm25=8.402, fused=0.02854)

## u01 - Correct refusal

**Question:** What is the capital of France?

**Best dense similarity:** 0.4569  |  **Refused:** True  |  **Key facts found:** [] of []  |  **Latency:** retrieve 36.2 ms, generate 0.0 ms

**Answer:**

> I couldn't find this in the Rust Book.

**Retrieved sources:**

1. `ch08-02-strings::010::aa5af6` - Common Collections > Storing UTF-8 Encoded Text with Strings > Indexing into Strings > Internal Representation (dense=0.4189, bm25=5.975, fused=0.03041)
2. `appendix-06-translation::000::eaf2be` - F - Translations of the Book > Appendix F: Translations of the Book (dense=0.4569, bm25=None, fused=0.01639)
3. `ch12-05-working-with-environment-variables::002::97afd1` - An I/O Project: Building a Command Line Program > Working with Environment Variables > Writing a Failing Test for Case-Insensitive Search (dense=None, bm25=6.576, fused=0.01639)
4. `ch06-02-match::004::779504` - Enums and Pattern Matching > The match Control Flow Construct > Patterns That Bind to Values (dense=0.4361, bm25=None, fused=0.01613)

## u02 - Correct refusal

**Question:** How do I write a list comprehension in Python?

**Best dense similarity:** 0.6854  |  **Refused:** True  |  **Key facts found:** [] of []  |  **Latency:** retrieve 49.6 ms, generate 0.0 ms

**Answer:**

> I couldn't find this in the Rust Book.

**Retrieved sources:**

1. `ch01-02-hello-world::006::871c52` - Getting Started > Hello, World! > Compilation and Execution (dense=None, bm25=11.42, fused=0.01639)
2. `ch04-03-slices::002::d36472` - Understanding Ownership > The Slice Type (dense=0.6854, bm25=None, fused=0.01639)
3. `ch13-01-closures::009::8fbff1` - Functional Language Features: Iterators and Closures > Closures > Capturing References or Moving Ownership (dense=None, bm25=8.118, fused=0.01613)
4. `ch19-01-all-the-places-for-patterns::008::a95307` - Patterns and Matching > All the Places Patterns Can Be Used > for Loops (dense=0.6622, bm25=None, fused=0.01613)

## u10 - Missed refusal (failure)

**Question:** How do I declare a goroutine and a WaitGroup in Go?

**Best dense similarity:** 0.7076  |  **Refused:** False  |  **Key facts found:** [] of []  |  **Latency:** retrieve 53.2 ms, generate 4716.0 ms

**Answer:**

> To declare a goroutine and a WaitGroup in Go, you can use the `go` keyword followed by the name of the goroutine and the type of the WaitGroup. Here's an example:
> 
> ```go
> package main
> 
> import (
> 	"fmt"
> 	"time"
> )
> 
> func main() {
> 	// Define a goroutine
> 	go func() {
> 		fmt.Println("Hello, world!")
> 	}()
> 
> 	// Define a WaitGroup
> 	var wg sync.WaitGroup
> 
> 	// Start the goroutine
> 	go func() {
> 		wg.Add(1)
> 		defer wg.Done()
> 		fmt.Println("Hello, world!")
> 	}()
> 
> 	// Wait for the goroutine to finish
> 	wg.Wait()
> }
> ```
> 
> In this example, the `main` function defines a goroutine named `go func() { ... }` that prints "Hello, world!" to the console. The `wg` variable is a `sync.WaitGroup` that will wait for the `go` function to finish. The `wg.Add(1)` line adds a new goroutine to the WaitGroup, and the `wg.Done()` line signals the WaitGroup to stop waiting. Finally, the `wg.Wait()` line waits for the WaitGroup to finish.

**Retrieved sources:**

1. `ch07-04-bringing-paths-into-scope-with-the-use-keyword::002::343532` - Packages, Crates, and Modules > Bringing Paths into Scope with the use Keyword > Creating Idiomatic use Paths (dense=0.7076, bm25=None, fused=0.01639)
2. `ch20-01-unsafe-rust::020::9e2d3f` - Advanced Features > Unsafe Rust > Implementing an Unsafe Trait (dense=None, bm25=7.819, fused=0.01639)
3. `ch09-02-recoverable-errors-with-result::012::6186f7` - Error Handling > Recoverable Errors with Result > Propagating Errors > The ? Operator Shortcut (dense=None, bm25=6.407, fused=0.01613)
4. `ch17-03-more-futures::002::f21d97` - Fundamentals of Asynchronous Programming: Async, Await, Futures, and Streams > Yielding Control to the Runtime (dense=0.6977, bm25=None, fused=0.01613)
