export type RouteId = "home" | "wrong-items" | "compare";

export type AppRoute = {
  id: RouteId;
  path: string;
  label: string;
};

export const routes: AppRoute[] = [
  { id: "home", path: "/", label: "首页" },
  { id: "wrong-items", path: "/wrong-items", label: "错题分析" },
  { id: "compare", path: "/compare", label: "模型比较" },
];

export function resolveRoute(pathname: string): AppRoute {
  return routes.find((route) => route.path === pathname) ?? routes[0];
}
