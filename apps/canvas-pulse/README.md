# Canvas Pulse

Canvas Pulse is a dependency-free Canvas Extension that turns `/server_info`
into a live operational dashboard. It demonstrates the complete host API v1
page workflow:

- registering a sidebar page;
- making an authenticated Agent Server request;
- navigating to a nested extension route; and
- cleaning up polling when the page unmounts.

The checked-in `extension.js` is already a self-contained browser ESM bundle.
