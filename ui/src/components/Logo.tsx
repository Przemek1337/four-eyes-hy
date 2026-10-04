/** Four dots (two pairs of eyes) and the name. The dots are decoration; the text names the product. */
export function Logo() {
  return (
    <span className="logo">
      <span className="eyes" aria-hidden="true"><i /><i /><i /><i /></span>
      <span className="logo-name">FourEyes</span>
    </span>
  );
}
