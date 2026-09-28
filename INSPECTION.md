# ASD-NEW reference inspection

The requested reference is [9059Rohith/ASD-NEW](https://github.com/9059Rohith/ASD-NEW). It is a Tamil speech-practice platform, so its domain models, therapy routes, curriculum, games, media and clinical copy are unrelated to Sahaya.

| Area | Decision | Reason |
| --- | --- | --- |
| Frontend assets, child-focused theme and mascot | Inspiration only | Calm interaction and language handling are useful patterns; visuals and content do not suit public-service response. |
| React component and route organization | Refactor conceptually | The reference uses Vite/React and many feature screens; Sahaya uses Next.js with a smaller domain-oriented surface. |
| Backend FastAPI structure | Inspiration only | Clear routers and local-first service ideas carry over; speech and clinical endpoints do not. |
| Authentication/privacy patterns | Refactor conceptually | The reference separates roles and uses consent; Sahaya implements its own object authorization and HTTP-only browser session. |
| Speech scoring models, child progress and rewards | Remove from scope | Unrelated to civic need coordination. |
| Fonts and accessibility principles | Reuse pattern | Readable multilingual typography and predictable controls inform the new tokens and layout. |

No ASD-specific application code or data was copied into Sahaya. The repository was inspected as a public design and engineering reference.
