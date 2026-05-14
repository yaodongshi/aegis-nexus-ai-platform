## 1. Implementation

- [x] 1.1 Add `/admin` as the primary backend management route and keep `/provider-console` as a compatibility alias.
- [x] 1.2 Update backend admin UI labels from Provider Console to Team AI Admin Console.
- [x] 1.3 Update tests to verify both the new primary route and the compatibility route.
- [x] 1.4 Update operator documentation to distinguish admin entrypoint, member workspace, and internal services.

## 2. Validation

- [x] 2.1 Run the backend unit tests for the touched slice.
- [x] 2.2 Verify `/admin` and `/provider-console` both return the admin page.