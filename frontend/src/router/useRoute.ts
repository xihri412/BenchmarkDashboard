import { useEffect, useMemo, useState } from "react";

import { resolveRoute } from "./routes";

export function useRoute() {
  const [pathname, setPathname] = useState(() => window.location.pathname);

  useEffect(() => {
    const handlePopState = () => setPathname(window.location.pathname);
    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, []);

  const activeRoute = useMemo(() => resolveRoute(pathname), [pathname]);

  const navigate = (path: string) => {
    if (path === window.location.pathname) {
      return;
    }

    window.history.pushState({}, "", path);
    setPathname(path);
  };

  return { activeRoute, navigate };
}
