import React from "react";
import { Link } from "react-router-dom";
import { ChevronRight } from "lucide-react";

export function PageHeader({
  title,
  subtitle,
  description,
  badge = null,
  actions = null,
  breadcrumb = null,
  breadcrumbs = null,
}) {
  const textDesc = subtitle || description;
  const crumbs = breadcrumbs || (breadcrumb ? [breadcrumb] : null);

  return (
    <div className="border-b border-slate-800 pb-4 mb-6">
      {crumbs && (
        <div className="mb-2 flex items-center gap-1.5 text-xs font-medium text-slate-400">
          {Array.isArray(crumbs) ? (
            crumbs.map((crumb, idx) => (
              <React.Fragment key={idx}>
                {idx > 0 && <ChevronRight size={12} className="text-slate-600" />}
                {typeof crumb === "string" ? (
                  <span>{crumb}</span>
                ) : crumb?.href ? (
                  <Link to={crumb.href} className="hover:text-slate-200 transition-colors">
                    {crumb.label}
                  </Link>
                ) : (
                  <span className="text-slate-300 font-semibold">{crumb.label || crumb}</span>
                )}
              </React.Fragment>
            ))
          ) : (
            <div>{crumbs}</div>
          )}
        </div>
      )}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-2xl font-bold tracking-tight text-white">{title}</h1>
            {badge && <div>{badge}</div>}
          </div>
          {textDesc && (
            <p className="mt-1 text-sm text-slate-400 leading-relaxed max-w-3xl">
              {textDesc}
            </p>
          )}
        </div>
        {actions && <div className="flex items-center gap-2.5 flex-shrink-0">{actions}</div>}
      </div>
    </div>
  );
}

export default PageHeader;

