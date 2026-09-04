import type {Metadata} from 'next';
import './globals.css';
import { Shell } from '@/components/layout/shell';

export const metadata: Metadata = {
  title: 'PragatiSetu - Operational Status',
  description: 'Industrial Integrity Modern Dashboard',
};

export default function RootLayout({children}: {children: React.ReactNode}) {
  return (
    <html lang="en">
      <body suppressHydrationWarning>
        <Shell>{children}</Shell>
      </body>
    </html>
  );
}
