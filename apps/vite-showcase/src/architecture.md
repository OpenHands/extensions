# One bundle, normal source

The source stays modular while Vite folds React, styles, assets, lazy modules, and the Worker into one browser ESM file. Canvas can import that file from a Blob URL without resolving anything beside it.

Every mount owns its resources. Unmounting aborts pending work, removes the keyboard listener and styles, terminates the Worker, and unmounts the React tree.
