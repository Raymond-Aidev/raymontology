import * as React from "react"

import { cn } from "@/lib/utils"

function Input({ className, type, ...props }: React.ComponentProps<"input">) {
  return (
    <input
      type={type}
      data-slot="input"
      className={cn(
        // Light input
        "h-9 w-full min-w-0 rounded-lg px-3 py-1 text-sm",
        "bg-white border border-gray-300 text-gray-900",
        "placeholder:text-gray-400",
        "shadow-sm transition-all outline-none",
        // Focus state
        "focus:border-[#5E6AD2]/50 focus:ring-2 focus:ring-[#5E6AD2]/20",
        // File input
        "file:inline-flex file:h-7 file:border-0 file:bg-gray-100 file:text-sm file:font-medium file:text-gray-700 file:rounded file:px-2 file:mr-2",
        // Disabled state
        "disabled:pointer-events-none disabled:cursor-not-allowed disabled:opacity-50",
        // Selection
        "selection:bg-[#5E6AD2]/30 selection:text-gray-900",
        // Invalid state
        "aria-invalid:border-red-500/50 aria-invalid:ring-red-500/20",
        className
      )}
      {...props}
    />
  )
}

export { Input }
