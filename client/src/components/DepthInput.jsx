import { useState } from "react";
import { formatDepth } from "../services/assaySelection";

// Formatting never changes the parent's raw value or the precision sent to the API.
export default function DepthInput({ value, ...props }) {
  const [focused, setFocused] = useState(false);
  return (
    <input
      {...props}
      type="number"
      step="any"
      value={focused ? value : formatDepth(value)}
      onFocus={() => setFocused(true)}
      onBlur={() => setFocused(false)}
    />
  );
}
