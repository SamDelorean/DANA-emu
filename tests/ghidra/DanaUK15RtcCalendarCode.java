// @category Dana
import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.Instruction;
import java.io.*;
public class DanaUK15RtcCalendarCode extends GhidraScript {
 public void run() throws Exception{
  PrintWriter o=new PrintWriter(new FileWriter(getScriptArgs()[0]));
  long[][] sites={{0x100800e0L,0x10080185L},{0x1007fd00L,0x1007fd80L},{0x10082b90L,0x10082c20L},{0x10080190L,0x10080210L}};
  for(long[] range:sites){
   o.printf("RANGE %08X .. %08X\n",range[0],range[1]);
   for(long pc=range[0];pc<range[1];){
    Instruction ins=getInstructionAt(toAddr(pc));
    if(ins==null){try{disassemble(toAddr(pc));}catch(Exception e){}ins=getInstructionAt(toAddr(pc));}
    if(ins!=null){o.printf("%08X %s\n",pc,ins.toString());pc+=ins.getLength();}
    else {o.printf("%08X ??\n",pc);pc+=2;}
   }
  }
  o.close();
 }
}
