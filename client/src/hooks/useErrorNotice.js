import { useCallback, useEffect, useRef, useState } from "react";

// Each occurrence has an identity, even when its message repeats.
export default function useErrorNotice() {
  const [notice, setNotice] = useState(null);
  const occurrence = useRef(0);
  const report = useCallback((message) => {
    setNotice(
      message ? { message: String(message), id: ++occurrence.current } : null,
    );
  }, []);
  useEffect(() => {
    if (!notice) return;
    const timer = setTimeout(() => setNotice(null), 5500);
    return () => clearTimeout(timer);
  }, [notice]);
  return [notice, report];
}
