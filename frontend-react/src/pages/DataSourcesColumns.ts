// Define the expected data shape (matches DataSourceApiResponse in DataSourcesPage.tsx)
interface DataSource {
  id: number;
  name: string;
  url: string;
  description?: string | null;
  last_scraped?: string | null;
  proposalCount?: number;
  last_checked?: string | null;
  status?: string;
}

// Import the ColumnDef type from your table library
// Assuming @tanstack/react-table, used by ShadCN UI's DataTable
import { ColumnDef } from "@tanstack/react-table";

// Define the columns
export const columns: ColumnDef<DataSource>[] = [
  {
    accessorKey: "id",
    header: "ID",
  },
  {
    accessorKey: "name",
    header: "Name",
  },
  {
    accessorKey: "url",
    header: "URL",
    // Optional: Render URL as a clickable link
    cell: ({ row }) => {
      const url = row.getValue("url") as string;
      try {
        // Attempt to create a URL object to validate and potentially display hostname
        const urlObj = new URL(url);
        return <a href={url} target="_blank" rel="noopener noreferrer" title={url}>{urlObj.hostname}</a>;
      } catch (e) {
        // If URL is invalid or relative, display as text
        return <span>{url}</span>;
      }
    },
  },
  {
    accessorKey: "status",
    header: "Status",
  },
  {
    accessorKey: "proposalCount",
    header: "Proposals",
  },
  {
    accessorKey: "last_checked",
    header: "Last Checked",
    // Optional: Format the date string
    cell: ({ row }) => {
      const dateString = row.getValue("last_checked") as string | null;
      if (!dateString) return "N/A";
      try {
        return new Date(dateString).toLocaleString();
      } catch (e) {
        return dateString; // Show raw string if formatting fails
      }
    },
  },
  // Add more columns as needed (e.g., actions, last_scraped, description)
]; 