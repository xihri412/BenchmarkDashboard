import "./styles.css";

import { AppLayout } from "./layout/AppLayout";
import { Compare } from "./pages/Compare";
import { Home } from "./pages/Home";
import { WrongItems } from "./pages/WrongItems";
import { useRoute } from "./router/useRoute";

export function App() {
  const { activeRoute, navigate } = useRoute();

  const page = {
    home: <Home />,
    "wrong-items": <WrongItems />,
    compare: <Compare />,
  }[activeRoute.id];

  return (
    <AppLayout activeRoute={activeRoute} onNavigate={navigate}>
      {page}
    </AppLayout>
  );
}
