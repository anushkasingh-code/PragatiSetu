import type {Metadata} from 'next';
import './globals.css';
import { Shell } from '@/components/layout/shell';
import { ProjectProvider } from '@/lib/project-context';

export const metadata: Metadata = {
  title: 'PragatiSetu - Operational Status',
  description: 'Industrial Integrity Modern Dashboard',
};

export default function RootLayout({children}: {children: React.ReactNode}) {
  return (
    <html lang="en">
      <body suppressHydrationWarning>
        <ProjectProvider>
          <Shell>{children}</Shell>
        </ProjectProvider>
      </body>
    </html>
  );
}
