// license:BSD-3-Clause
// @category Dana
// Invoke with -readOnly -noanalysis on the existing UK1.5 project.
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.*;
import ghidra.program.model.listing.*;
import java.io.*;
public class DanaPowerAdcAudit extends GhidraScript {
 public void run() throws Exception {
  Address start=toAddr(0x1007b0bcL),end=toAddr(0x1007b31dL);
  Function old=getFunctionContaining(start);
  if(old!=null)currentProgram.getFunctionManager().removeFunction(old.getEntryPoint());
  clearListing(start,end);disassemble(start);
  for(int pass=0;pass<12;pass++){
   InstructionIterator it=currentProgram.getListing().getInstructions(start,true);
   while(it.hasNext()){
    Instruction ins=it.next();if(ins.getAddress().compareTo(end)>0)break;
    if(ins.getMnemonicString().equalsIgnoreCase("trap")){
     ins.setFallThrough(ins.getMaxAddress().add(3));disassemble(ins.getMaxAddress().add(3));
    }
   }
  }
  try(PrintWriter out=new PrintWriter(new FileWriter(getScriptArgs()[0]))){
   InstructionIterator it=currentProgram.getListing().getInstructions(start,true);
   while(it.hasNext()){
    Instruction ins=it.next();if(ins.getAddress().compareTo(end)>0)break;
    out.println(ins.getAddress()+" "+ins);
   }
  }
  println("H5_ADC_READONLY_AUDIT_DONE");
 }
}
