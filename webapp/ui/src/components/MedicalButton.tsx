import React from 'react';
import { Button, type ButtonProps } from '@/components/ui/button';
import { cn } from '@/lib/utils';

export type MedicalButtonProps = ButtonProps;

const MedicalButton = React.forwardRef<HTMLButtonElement, MedicalButtonProps>(
  ({ className, size = 'lg', ...props }, ref) => {
    return (
      <Button
        ref={ref}
        size={size}
        className={cn(size === 'icon' && 'rounded-lg', className)}
        {...props}
      />
    );
  }
);

MedicalButton.displayName = 'MedicalButton';

export { MedicalButton };
export default MedicalButton;
