export default function ErrorBanner({ message }) {
  if (!message) return null;

  return (
    <div className="rounded-lg bg-red-light px-4 py-3 text-sm text-red">
      {message}
    </div>
  );
}
